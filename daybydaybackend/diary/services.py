from .models import Diary, DiaryEmotion
from .emotion_analyzer import EmotionAnalyzer


# ===== 일기 작성 비즈니스 로직 =====
def create_diary_entry(user, content, weather=None, image=None):
    """
    새로운 일기를 작성하여 저장하는 로직
    """
    diary = Diary.objects.create(user=user, content=content, weather=weather, image=image)
    return diary



# ===== 감정 분석 비즈니스 로직 =====
def process_diary_emotion(diary_id, user):
    """
    일기 ID를 기반으로 AI 분석을 수행하고 DB에 결과를 반영하는 비즈니스 로직
    """
    # 1. 유저 권한 및 일기 존재 여부 확인
    diary = Diary.objects.get(id=diary_id, user=user)
    
    # 2. Kiwi + 감정사전 + 선택적 Gemini fallback 분석
    emotion_dict = analyze_emotion_hybrid(diary.content)
    
    # 3. 데이터 갱신 또는 생성
    DiaryEmotion.objects.update_or_create(
        diary=diary,
        defaults={
            'joy': emotion_dict.get('joy', 0.0),
            'sadness': emotion_dict.get('sadness', 0.0),
            'anger': emotion_dict.get('anger', 0.0),
            'fear': emotion_dict.get('fear', 0.0),
            'trust': emotion_dict.get('trust', 0.0),
            'surprise': emotion_dict.get('surprise', 0.0),
            'valence': emotion_dict.get('valence', 0.0),
            'arousal': emotion_dict.get('arousal', 0.0),
            'primary_emotion': emotion_dict.get('primary_emotion', '알수없음')
        }
    )
    return diary

_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = EmotionAnalyzer()
    return _analyzer

def analyze_emotion_hybrid(text: str) -> dict:
    """
    Kiwi 형태소 분석 + NRC/KNU 사전 + 선택적 Gemini fallback 기반 감정 분석
    """
    emotion_6d = get_analyzer().analyze(text)
    valence = _compute_valence(emotion_6d)
    arousal = _compute_arousal(emotion_6d)
    primary_emotion = _primary_emotion(emotion_6d)

    return {
        **emotion_6d,
        'valence': valence,
        'arousal': arousal,
        'primary_emotion': primary_emotion,
    }


def _compute_valence(emotions: dict) -> float:
    positive = (emotions.get('joy', 0.0) + emotions.get('trust', 0.0)) / 2.0
    negative = (
        emotions.get('sadness', 0.0)
        + emotions.get('anger', 0.0)
        + emotions.get('fear', 0.0)
    ) / 3.0
    value = positive - negative
    return round(max(-1.0, min(1.0, value)), 4)


def _compute_arousal(emotions: dict) -> float:
    active = (emotions.get('anger', 0.0) + emotions.get('surprise', 0.0)) / 2.0
    calm = (emotions.get('sadness', 0.0) + emotions.get('trust', 0.0)) / 2.0
    value = active - calm
    return round(max(-1.0, min(1.0, value)), 4)


def _primary_emotion(emotions: dict) -> str:
    if not emotions:
        return '알수없음'

    label_map = {
        'joy': '기쁨',
        'sadness': '슬픔',
        'anger': '분노',
        'fear': '두려움',
        'trust': '신뢰',
        'surprise': '놀람',
    }
    key = max(label_map.keys(), key=lambda k: emotions.get(k, 0.0))
    if emotions.get(key, 0.0) <= 0:
        return '알수없음'
    return label_map[key]


def get_user_recent_average_emotion(user):
    """
    유저의 최근 5개 일기의 감정 데이터를 평균내어 반환합니다.
    일기 데이터가 없거나 감정 분석 결과가 없으면 None을 반환합니다.
    """
    diaries = Diary.objects.filter(user=user).select_related('emotion')[:5]
    emotions = [d.emotion for d in diaries if hasattr(d, 'emotion') and d.emotion is not None]
    if not emotions:
        return None, diaries
    
    count = len(emotions)
    avg_emotion = {
        'joy': round(sum(e.joy for e in emotions) / count, 4),
        'sadness': round(sum(e.sadness for e in emotions) / count, 4),
        'anger': round(sum(e.anger for e in emotions) / count, 4),
        'fear': round(sum(e.fear for e in emotions) / count, 4),
        'trust': round(sum(e.trust for e in emotions) / count, 4),
        'surprise': round(sum(e.surprise for e in emotions) / count, 4),
        'valence': round(sum(e.valence for e in emotions) / count, 4),
        'arousal': round(sum(e.arousal for e in emotions) / count, 4),
    }
    return avg_emotion, diaries



