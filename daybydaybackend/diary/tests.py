from django.test import TestCase
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from daybydaybackend.diary.models import Diary, DiaryEmotion
from daybydaybackend.diary.services import determine_auto_recommendation_mode

class EmotionAutoModeTestCase(TestCase):
    def setUp(self):
        # 테스트용 유저 생성
        self.user = User.objects.create_user(username='testuser', password='password123')

    def create_diary_with_emotion(self, content, delta_days, emotion_scores, primary_emotion='알수없음'):
        """
        특정 시간차(delta_days 전)를 두고 일기 및 감정 데이터를 생성하는 헬퍼 함수
        """
        diary = Diary.objects.create(
            user=self.user,
            content=content,
        )
        # created_at 필드는 auto_now_add=True 이므로 직접 수정이 불가하여 django model 쿼리로 update 처리
        mock_time = datetime.now() - timedelta(days=delta_days)
        Diary.objects.filter(id=diary.id).update(created_at=mock_time)
        diary.refresh_from_db()

        # DiaryEmotion 생성
        DiaryEmotion.objects.create(
            diary=diary,
            joy=emotion_scores.get('joy', 0.0),
            sadness=emotion_scores.get('sadness', 0.0),
            anger=emotion_scores.get('anger', 0.0),
            fear=emotion_scores.get('fear', 0.0),
            trust=emotion_scores.get('trust', 0.0),
            surprise=emotion_scores.get('surprise', 0.0),
            valence=emotion_scores.get('valence', 0.0),
            arousal=emotion_scores.get('arousal', 0.0),
            primary_emotion=primary_emotion
        )
        return diary

    def test_stagnation_by_variance_leads_to_shift(self):
        """
        테스트 1: 최근 5일의 sadness 수치가 거의 변동성 없이 높은 수준으로 유지될 때 (Stagnation)
        -> shift 모드가 결정되는지 확인
        """
        # 5일간의 우울 지수: [0.4, 0.42, 0.38, 0.41, 0.39]
        # 평균: 0.40, 분산: 0.00025 (임계값 0.025보다 매우 작음)
        self.create_diary_with_emotion("우울한 날 1", 4, {'sadness': 0.40}, '슬픔')
        self.create_diary_with_emotion("우울한 날 2", 3, {'sadness': 0.42}, '슬픔')
        self.create_diary_with_emotion("우울한 날 3", 2, {'sadness': 0.38}, '슬픔')
        self.create_diary_with_emotion("우울한 날 4", 1, {'sadness': 0.41}, '슬픔')
        current_diary = self.create_diary_with_emotion("오늘 일기", 0, {'sadness': 0.39}, '슬픔')

        mode = determine_auto_recommendation_mode(self.user, current_diary)
        self.assertEqual(mode, 'shift')

    def test_stagnation_by_continuity_leads_to_shift(self):
        """
        테스트 2: 부정적인 감정(슬픔)이 3회 연속 대표 감정으로 고착된 경우
        -> 분산 수치와 관계없이 shift 모드가 결정되는지 확인
        """
        # 대표 감정이 연속 3일 '슬픔'인 상태
        self.create_diary_with_emotion("일기 1", 4, {'sadness': 0.2}, '기쁨')
        self.create_diary_with_emotion("일기 2", 3, {'sadness': 0.1}, '신뢰')
        self.create_diary_with_emotion("일기 3", 2, {'sadness': 0.5}, '슬픔')
        self.create_diary_with_emotion("일기 4", 1, {'sadness': 0.6}, '슬픔')
        current_diary = self.create_diary_with_emotion("오늘 일기", 0, {'sadness': 0.5}, '슬픔')

        mode = determine_auto_recommendation_mode(self.user, current_diary)
        self.assertEqual(mode, 'shift')

    def test_volatility_leads_to_maintain(self):
        """
        테스트 3: 부정적인 감정(분노)의 평균은 높지만 분산이 커서 감정이 요동친 경우 (Volatility)
        -> 일시적인 기분 스파이크로 해석하여 maintain 모드가 결정되는지 확인
        """
        # 5일간의 분노 지수: [0.0, 0.1, 0.05, 0.9, 0.8]
        # 평균: 0.37 (임계값 0.35 초과), 분산: 0.198 (임계값 0.025보다 큼)
        self.create_diary_with_emotion("일기 1", 4, {'anger': 0.0}, '기쁨')
        self.create_diary_with_emotion("일기 2", 3, {'anger': 0.1}, '신뢰')
        self.create_diary_with_emotion("일기 3", 2, {'anger': 0.05}, '기쁨')
        self.create_diary_with_emotion("일기 4", 1, {'anger': 0.9}, '분노')
        current_diary = self.create_diary_with_emotion("오늘 일기", 0, {'anger': 0.8}, '분노')

        mode = determine_auto_recommendation_mode(self.user, current_diary)
        self.assertEqual(mode, 'maintain')

    def test_positive_stagnation_leads_to_amplification(self):
        """
        테스트 4: 오늘 대표 감정이 '기쁨'이고, 최근 5일간 joy의 평균이 0.3 이상으로 긍정이 지속될 때
        -> amplification 모드가 결정되는지 확인
        """
        # 5일간의 기쁨 지수: [0.55, 0.60, 0.58, 0.62, 0.65] -> 평균: ~0.6 (임계값 0.5 초과)
        self.create_diary_with_emotion("기쁜 날 1", 4, {'joy': 0.55}, '기쁨')
        self.create_diary_with_emotion("기쁜 날 2", 3, {'joy': 0.60}, '기쁨')
        self.create_diary_with_emotion("기쁜 날 3", 2, {'joy': 0.58}, '기쁨')
        self.create_diary_with_emotion("기쁜 날 4", 1, {'joy': 0.62}, '기쁨')
        current_diary = self.create_diary_with_emotion("오늘 너무 행복하다", 0, {'joy': 0.65}, '기쁨')

        mode = determine_auto_recommendation_mode(self.user, current_diary)
        self.assertEqual(mode, 'amplification')

    def test_default_flat_state_leads_to_maintain(self):
        """
        테스트 5: 뚜렷한 감정 쏠림이나 고착이 없는 평범한 감정 패턴일 때
        -> 기본값인 maintain 모드가 결정되는지 확인
        """
        # 평탄한 상태: 기쁨과 슬픔 등이 혼재되어 있고 점수가 낮음
        self.create_diary_with_emotion("일기 1", 4, {'joy': 0.1, 'sadness': 0.1}, '알수없음')
        self.create_diary_with_emotion("일기 2", 3, {'joy': 0.2, 'sadness': 0.0}, '알수없음')
        self.create_diary_with_emotion("일기 3", 2, {'joy': 0.1, 'sadness': 0.1}, '알수없음')
        self.create_diary_with_emotion("일기 4", 1, {'joy': 0.15, 'sadness': 0.05}, '알수없음')
        current_diary = self.create_diary_with_emotion("오늘 일기", 0, {'joy': 0.1, 'sadness': 0.1}, '알수없음')

        mode = determine_auto_recommendation_mode(self.user, current_diary)
        self.assertEqual(mode, 'maintain')
