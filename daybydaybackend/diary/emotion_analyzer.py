# pyright: reportMissingImports=false

import json
import logging
import re
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from datetime import datetime
from google import genai

try:
    from kiwipiepy import Kiwi
except ImportError:  # pragma: no cover - 런타임 환경에 따라 의존성이 없을 수 있음
    Kiwi = None


EMOTION_KEYS = ("joy", "sadness", "anger", "fear", "trust", "surprise")
logger = logging.getLogger(__name__)


class EmotionAnalyzer:
    def __init__(self):
        self.kiwi = Kiwi() if Kiwi is not None else None
        self.nrc_lexicon = self._load_lexicon("nrc_lexicon_ko.json")
        self.knu_lexicon = self._load_lexicon("knu_lexicon_ko.json")
        self._client = None
        self._analysis_total = 0
        self._analysis_with_fallback = 0

    def analyze(self, text: str) -> dict:
        tokens = self.tokenize_and_filter(text)
        if not tokens:
            return self._empty_emotions()

        scores = self._zero_scores()
        unresolved = []
        matched_count = 0

        for token in tokens:
            token_scores = self._lookup_token_scores(token)
            if self._has_signal(token_scores):
                matched_count += 1
                self._accumulate(scores, token_scores)
            else:
                unresolved.append(token)

        has_dictionary_signal = self._has_signal(scores)
        fallback_scores = self._zero_scores()
        should_call_gemini = self._should_call_gemini(
            text=text,
            tokens=tokens,
            matched_count=matched_count,
            unresolved=unresolved,
            has_dictionary_signal=has_dictionary_signal
        )
        coverage = matched_count / len(tokens) if tokens else 0.0

        self._analysis_total += 1
        if should_call_gemini:
            self._analysis_with_fallback += 1
        self._log_analysis_stats(
            token_count=len(tokens),
            matched_count=matched_count,
            unresolved_count=len(unresolved),
            coverage=coverage,
            used_fallback=should_call_gemini,
        )

        if should_call_gemini:
            fallback_scores = self._analyze_unresolved_with_gemini(text=text, unresolved=unresolved)

        if has_dictionary_signal and self._has_signal(fallback_scores):
            merged = {
                key: (scores[key] * 0.7) + (fallback_scores[key] * 0.3)
                for key in EMOTION_KEYS
            }
        elif has_dictionary_signal:
            merged = scores
        else:
            merged = fallback_scores

        normalized = self._normalize_scores(merged)
        return normalized

    def tokenize_and_filter(self, text: str) -> list[str]:
        if self.kiwi is None:
            raw_tokens = [SimpleToken(part) for part in re.split(r"\s+", text) if part.strip()]
        else:
            raw_tokens = self.kiwi.tokenize(text)
        filtered = []
        for tok in raw_tokens:
            word = tok.form.strip().lower()
            tag = tok.tag

            if not word:
                continue
            if self._is_filtered_pos(tag):
                continue
            if self._is_meaningless_token(word):
                continue
            filtered.append(word)
        return filtered

    def _is_filtered_pos(self, tag: str) -> bool:
        # 기능어/기호/숫자/웹토큰 계열은 분석에서 제외한다.
        filtered_prefixes = ("J", "E", "X", "S", "W")
        filtered_exact = {
            "SF", "SP", "SS", "SE", "SO", "SW", "SH", "SN", "NR", "NP",
            "W_URL", "W_EMAIL", "W_HASHTAG", "W_MENTION", "W_SERIAL",
        }
        if tag in filtered_exact or tag.startswith(filtered_prefixes):
            return True

        # 감정 분석에 기여가 낮은 품사는 제외
        if tag in {"MM", "IC"}:
            return True

        return False

    def _is_meaningless_token(self, token: str) -> bool:
        if len(token) <= 1:
            return True
        if re.fullmatch(r"[\d\W_]+", token):
            return True
        stopwords = {
            "그리고", "그래서", "하지만", "근데", "그냥", "정말", "진짜",
            "너무", "약간", "조금", "매우", "아주", "오늘", "어제", "내일",
            "같다", "것", "수", "좀", "때문", "완전", "진심", "약간은",
        }
        return token in stopwords

    def _lookup_token_scores(self, token: str) -> dict:
        scores = self._zero_scores()
        nrc = self.nrc_lexicon.get(token)
        knu = self.knu_lexicon.get(token)

        if nrc:
            self._accumulate(scores, nrc)
        if knu:
            self._accumulate(scores, knu)

        return scores

    def _is_quota_exceeded(self) -> bool:
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"gemini_quota:{today_str}"
        current_count = cache.get(cache_key, 0)
        limit = getattr(settings, "GEMINI_DAILY_LIMIT", 50)
        return current_count >= limit

    def _increment_quota(self) -> None:
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"gemini_quota:{today_str}"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, timeout=86400) # 24시간 동안 유효

    def _should_call_gemini(self, text: str, tokens: list[str], matched_count: int, unresolved: list[str], has_dictionary_signal: bool) -> bool:
        # 1차 방어막: 공백 제외 15자 미만의 너무 짧은 일기 차단
        clean_text = text.replace(" ", "").strip()
        if len(clean_text) < 15:
            logger.info("emotion-analysis | Gemini 호출 차단: 본문 15자 미만 (len=%s)", len(clean_text))
            return False

        # 2차 방어막: 형태소 분석을 통과한 유효 의미 토큰이 2개 미만일 때 차단
        if len(tokens) < 2:
            logger.info("emotion-analysis | Gemini 호출 차단: 유효 의미 토큰 수 부족 (count=%s)", len(tokens))
            return False

        # 3차 방어막: 일일 최대 API 쿼터 초과 여부 확인 (Circuit Breaker)
        if self._is_quota_exceeded():
            logger.warning("emotion-analysis | [WARNING] Gemini 호출 차단: 일일 API 쿼터 한도 초과!")
            return False

        # 사전 기반 분석에서 매칭된 감정 신호가 전혀 없고, 유효한 명사/동사/형사 분석 대상이 남아있을 때 백업 활성화
        return not has_dictionary_signal and bool(tokens)

    def _analyze_unresolved_with_gemini(self, text: str, unresolved: list[str]) -> dict:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return self._zero_scores()

        if self._client is None:
            self._client = genai.Client(api_key=api_key)

        unresolved_unique = list(dict.fromkeys(unresolved))[:20]
        prompt = f"""
[Emotion Analysis Task based on Robert Plutchik's Wheel of Emotions]
당신은 심리학자 Robert Plutchik의 감정 바퀴(Wheel of Emotions) 이론에 기반하여 사용자의 일기를 정밀 분석하는 전문 AI 감정 분석가입니다.

아래 6가지 핵심 감정 차원에 대해 일기 전체의 문맥적 정황을 파악하여 각각 0.0 ~ 1.0 범위의 실수 점수를 매겨주세요.
점수는 각 감정의 강도와 명확성을 의미합니다.

[감정 차원의 심리학적 평가 가이드라인 (Scoring Rubric)]
1. joy (기쁨): 일기에서 성취감, 만족, 기쁨, 따뜻함, 행복감을 표현한 강도.
2. sadness (슬픔): 실망, 우울, 상실감, 무력감, 외로움을 내포하고 있는 강도.
3. anger (분노): 불만, 짜증, 분노, 억울함, 적대감을 표출한 강도.
4. fear (공포/불안): 초조함, 걱정, 위협감, 불안감, 긴장 상태를 호소한 강도.
5. trust (신뢰/편안): 안정감, 안도감, 고마움, 타인이나 자신에 대한 수용/수긍의 강도.
6. surprise (놀람/당황): 예측하지 못한 일에 대한 경이로움, 놀라움, 혹은 당황스러운 감정의 강도.

[중요 규칙]
- 분석 대상인 일기 본문의 감정선을 전체적으로 종합하고, 아래 '사전 분석 실패 핵심 토큰'들이 풍기는 뉘앙스를 최우선으로 반영하세요.
- 각 감정 차원의 점수는 개별적으로 판단하며, 반드시 순수 JSON 형식만 반환하세요 (Markdown 백틱 ```json ... ``` 기호는 생략하거나 포함해도 무방하며, 순수 파싱이 가능해야 함).

[사전 분석 실패 핵심 토큰]:
{", ".join(unresolved_unique)}

[일기 본문]:
{text}

[반환 예시 (JSON)]:
{{
  "joy": 0.0,
  "sadness": 0.5,
  "anger": 0.2,
  "fear": 0.1,
  "trust": 0.0,
  "surprise": 0.0
}}
"""

        try:
            response = self._client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt,
            )
            result_text = response.text.strip()
            result_text = re.sub(r"^```(json)?\s*", "", result_text)
            result_text = re.sub(r"\s*```$", "", result_text)
            parsed = json.loads(result_text)
            
            clean = self._zero_scores()
            for key in EMOTION_KEYS:
                clean[key] = self._clamp_01(float(parsed.get(key, 0.0)))
            
            # API 호출 성공 및 쿼터 차감 기록
            self._increment_quota()
            return clean
        except Exception as e:
            logger.error("emotion-analysis | [ERROR] Gemini API 호출 또는 파싱 중 예외 발생: %s", str(e))
            return self._zero_scores()

    def _load_lexicon(self, filename: str) -> dict:
        data_dir = Path(__file__).resolve().parent / "data"
        lexicon_path = data_dir / filename
        if not lexicon_path.exists():
            return {}

        try:
            with lexicon_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            normalized = {}
            for key, value in data.items():
                normalized_key = str(key).strip().lower()
                if not normalized_key or not isinstance(value, dict):
                    continue
                normalized[normalized_key] = {
                    emotion: self._clamp_01(float(score))
                    for emotion, score in value.items()
                    if emotion in EMOTION_KEYS
                }
            return normalized
        except (json.JSONDecodeError, OSError, ValueError):
            return {}

    def _normalize_scores(self, scores: dict) -> dict:
        total = sum(max(0.0, scores.get(key, 0.0)) for key in EMOTION_KEYS)
        if total <= 0:
            return self._empty_emotions()

        return {
            key: round(max(0.0, scores.get(key, 0.0)) / total, 4)
            for key in EMOTION_KEYS
        }

    def _accumulate(self, target: dict, source: dict) -> None:
        for key in EMOTION_KEYS:
            target[key] += float(source.get(key, 0.0))

    def _has_signal(self, scores: dict) -> bool:
        return any(scores.get(key, 0.0) > 0 for key in EMOTION_KEYS)

    def _zero_scores(self) -> dict:
        return {key: 0.0 for key in EMOTION_KEYS}

    def _empty_emotions(self) -> dict:
        return self._zero_scores()

    def _clamp_01(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _log_analysis_stats(
        self,
        token_count: int,
        matched_count: int,
        unresolved_count: int,
        coverage: float,
        used_fallback: bool,
    ) -> None:
        fallback_ratio = (
            self._analysis_with_fallback / self._analysis_total
            if self._analysis_total
            else 0.0
        )
        logger.info(
            "emotion-analysis stats | tokens=%s matched=%s unresolved=%s coverage=%.3f "
            "fallback_used=%s fallback_ratio=%.3f total=%s",
            token_count,
            matched_count,
            unresolved_count,
            coverage,
            used_fallback,
            fallback_ratio,
            self._analysis_total,
        )


class SimpleToken:
    def __init__(self, form: str):
        self.form = form
        self.tag = "NNG"