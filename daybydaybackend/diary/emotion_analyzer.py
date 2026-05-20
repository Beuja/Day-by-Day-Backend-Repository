# pyright: reportMissingImports=false

import json
import logging
import re
from pathlib import Path

from django.conf import settings
from google import genai

try:
    from kiwipiepy import Kiwi
except ImportError:  # pragma: no cover - 런타임 환경에 따라 의존성이 없을 수 있음
    Kiwi = None


EMOTION_KEYS = ("joy", "sadness", "anger", "fear", "trust", "surprise")
logger = logging.getLogger(__name__)


DEFAULT_NRC_LEXICON = {
    "행복": {"joy": 1.0, "trust": 0.6},
    "기쁨": {"joy": 1.0, "surprise": 0.3},
    "즐겁": {"joy": 0.9},
    "신남": {"joy": 0.7, "surprise": 0.5},
    "슬픔": {"sadness": 1.0},
    "우울": {"sadness": 0.9, "fear": 0.2},
    "불안": {"fear": 0.8, "sadness": 0.2},
    "무섭": {"fear": 1.0},
    "화나": {"anger": 1.0},
    "분노": {"anger": 1.0},
    "짜증": {"anger": 0.8, "sadness": 0.2},
    "믿음": {"trust": 1.0},
    "신뢰": {"trust": 1.0},
    "놀람": {"surprise": 1.0},
    "당황": {"surprise": 0.7, "fear": 0.3},
}


DEFAULT_KNU_LEXICON = {
    "편안": {"trust": 0.5, "joy": 0.3},
    "안정": {"trust": 0.7},
    "만족": {"joy": 0.7, "trust": 0.3},
    "외롭": {"sadness": 0.8},
    "불쾌": {"anger": 0.4, "sadness": 0.6},
    "긴장": {"fear": 0.6, "surprise": 0.2},
}


class EmotionAnalyzer:
    def __init__(self):
        self.kiwi = Kiwi() if Kiwi is not None else None
        self.nrc_lexicon = self._load_lexicon("nrc_lexicon_ko.json", DEFAULT_NRC_LEXICON)
        self.knu_lexicon = self._load_lexicon("knu_lexicon_ko.json", DEFAULT_KNU_LEXICON)
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
        should_call_gemini = self._should_call_gemini(tokens, matched_count, unresolved)
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

    def _should_call_gemini(self, tokens: list[str], matched_count: int, unresolved: list[str]) -> bool:
        # 비용 절감: Gemini 호출 완전 비활성화
        # 사전 기반 분석만 수행하고, 추후 필요 시 재활성화
        return False

    def _analyze_unresolved_with_gemini(self, text: str, unresolved: list[str]) -> dict:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return self._zero_scores()

        if self._client is None:
            self._client = genai.Client(api_key=api_key)

        unresolved_unique = list(dict.fromkeys(unresolved))[:20]
        prompt = f"""
다음 한국어 일기 텍스트를 분석해서 아래 6개 감정에 대해 0.0~1.0 범위의 점수를 JSON으로 반환해라.

감정 차원:
- joy
- sadness
- anger
- fear
- trust
- surprise

중요 규칙:
- 아래 미분류 핵심 토큰 목록을 우선 참고해라.
- 조사, 접속어, 문장부호 같은 무의미 토큰은 무시해라.
- 결과는 반드시 순수 JSON만 반환해라.

미분류 핵심 토큰:
{", ".join(unresolved_unique)}

일기 본문:
{text}

반환 예시:
{{
  "joy": 0.3,
  "sadness": 0.1,
  "anger": 0.0,
  "fear": 0.2,
  "trust": 0.4,
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
            return clean
        except Exception:
            return self._zero_scores()

    def _load_lexicon(self, filename: str, default_data: dict) -> dict:
        data_dir = Path(__file__).resolve().parent / "data"
        lexicon_path = data_dir / filename
        if not lexicon_path.exists():
            return default_data

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
            return normalized or default_data
        except (json.JSONDecodeError, OSError, ValueError):
            return default_data

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
