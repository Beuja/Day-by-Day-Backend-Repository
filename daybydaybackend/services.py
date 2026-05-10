from google import genai
import json
import re
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Diary, DiaryEmotion

# ===== 유저 관련 비즈니스 로직 =====
def create_user_account(username, password, email=''):
    """새로운 사용자 계정을 생성하고 토큰을 발급하는 비즈니스 로직"""
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    token, _ = Token.objects.get_or_create(user=user)
    return user, token

def update_user_account(user, email=None, password=None):
    """기존 사용자의 정보를 안전하게 수정하는 비즈니스 로직"""
    if email is not None:
        user.email = email
        
    if password is not None:
        user.set_password(password) # 비밀번호는 반드시 해시화하여 저장
        
    user.save()
    return user

# ===== 일기 및 감정 분석 비즈니스 로직 =====
def create_diary_entry(user, content):
    """
    새로운 일기를 작성하여 저장하는 로직
    """
    diary = Diary.objects.create(user=user, content=content)
    return diary

def process_diary_emotion(diary_id, user):
    """
    일기 ID를 기반으로 AI 분석을 수행하고 DB에 결과를 반영하는 비즈니스 로직
    """
    # 1. 유저 권한 및 일기 존재 여부 확인
    diary = Diary.objects.get(id=diary_id, user=user) 
    
    # 2. Gemini API 호출
    emotion_dict = analyze_emotion_with_gemini(diary.content)
    
    # 3. 데이터 갱신 또는 생성
    DiaryEmotion.objects.update_or_create(
        diary=diary,
        defaults={
            'valence': emotion_dict.get('valence', 0.0),
            'arousal': emotion_dict.get('arousal', 0.0),
            'primary_emotion': emotion_dict.get('primary_emotion', '알수없음')
        }
    )
    return diary

# Gemini API를 사용하여 일기 텍스트에서 감정 분석을 수행하는 함수
def analyze_emotion_with_gemini(text: str) -> dict:
    """
    Gemini API를 사용하여 일기 텍스트에서 Russell's Circumplex Model 기반 감정 수치 추출
    """
    # 1. API 키 확인 (settings.py -> .env 에서 GEMINI_API_KEY 불러옴)
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        print("Warning: GEMINI_API_KEY is not set in settings.py")
        client = None
    else:
        # 2. Client 객체 초기화 (신구 google-genai 라이브러리 방식)
        client = genai.Client(api_key=api_key)
        
    # 3. Gemini에게 명령을 내릴 프롬프트 작성
    prompt = f"""
사용자의 일기를 읽고 러셀의 감정 원형 모델(Russell's Circumplex Model)에 따라 감정을 분석해라.
- Valence(유쾌도): -1.0(가장 불쾌) ~ 1.0(가장 유쾌)
- Arousal(각성도): -1.0(가장 차분) ~ 1.0(가장 흥분)
- primary_emotion: 이를 대표하는 한국어 감정 단어 하나

응답은 반드시 마크다운 포맷팅(```json 등)을 제외하고 순수한 JSON 형식으로만 반환해라.

형식 예시:
{{
    "valence": 0.5,
    "arousal": 0.2,
    "primary_emotion": "행복"
}}

일기 내용:
{text}
"""
    
    try:
        if client is None:
            raise Exception("API 클라이언트가 초기화되지 않았습니다.")
            
        # 4. 모델 호출 및 응답 받아오기 (최신 gemini-2.5-flash 모델 사용)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        result_text = response.text.strip()
        
        # 5. 응답 텍스트가 '```json' 같은 마크다운 블록으로 감싸져 올 경우를 대비해 텍스트 파싱
        result_text = re.sub(r'^```(json)?\s*', '', result_text)
        result_text = re.sub(r'\s*```$', '', result_text)
        
        # 6. JSON 문자열을 파이썬 딕셔너리로 변환
        emotion_data = json.loads(result_text)
        
        # 7. 데이터 추출 및 검증 (값이 비어있을 수 있으므로 기본값 세팅)
        valence = float(emotion_data.get('valence', 0.0))
        arousal = float(emotion_data.get('arousal', 0.0))
        primary_emotion = str(emotion_data.get('primary_emotion', '알수없음'))
        
        # 8. 수치가 -1.0 ~ 1.0 범위를 벗어나지 않도록 방어하는 로직 (Clamping)
        valence = max(-1.0, min(1.0, valence))
        arousal = max(-1.0, min(1.0, arousal))
        
        # 9. 최종 딕셔너리 반환
        return {
            "valence": valence,
            "arousal": arousal,
            "primary_emotion": primary_emotion
        }
        
    except Exception as e:
        # JSON 파싱 실패 혹은 API 호출 중 통신 에러 발생 시 예외 처리
        print(f"Gemini API Error: {str(e)}")
        return {
            "valence": 0.0,
            "arousal": 0.0,
            "primary_emotion": "분석불가"
        }
