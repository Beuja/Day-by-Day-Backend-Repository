from rest_framework import serializers
from .models import Diary, DiaryEmotion


class DiaryEmotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiaryEmotion
        fields = [
            'joy', 'sadness', 'anger', 'fear', 'trust', 'surprise',
            'valence', 'arousal', 'primary_emotion'
        ]


class DiarySerializer(serializers.ModelSerializer):
    emotion = DiaryEmotionSerializer(read_only=True)

    class Meta:
        model = Diary
        fields = ['id', 'content', 'created_at', 'emotion', 'weather', 'image']


class AnalyzeEmotionRequestSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField()


class DiaryCreateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diary
        fields = ['content', 'weather', 'image']


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        from daybydaybackend.music_movie.models import Movie
        model = Movie
        fields = '__all__'
        ref_name = 'DiaryMovieSerializer'


class MusicSerializer(serializers.ModelSerializer):
    class Meta:
        from daybydaybackend.music_movie.models import Music
        model = Music
        fields = '__all__'
        ref_name = 'DiaryMusicSerializer'


class MainRecommendationResponseSerializer(serializers.Serializer):
    has_diaries = serializers.BooleanField(help_text="해당 유저의 최근 일기 작성 데이터가 존재하여 추천이 가능한지 여부")
    is_fallback = serializers.BooleanField(default=False, help_text="도서 추천이 사용량 부족 등으로 대체(Fallback) 추천되었는지 여부")
    emotion_status = DiaryEmotionSerializer(help_text="최근 5개 일기의 Plutchik 6대 감정 평균 수치 (일기가 전혀 없으면 null)", allow_null=True)
    books = serializers.ListField(child=serializers.DictField(), help_text="맞춤형 추천 도서 목록 2개 (일기가 전혀 없으면 빈 배열)")
    music = serializers.ListField(child=serializers.DictField(), help_text="맞춤형 추천 음악 목록 2개 (일기가 전혀 없으면 빈 배열)")
    movies = serializers.ListField(child=serializers.DictField(), help_text="맞춤형 추천 영화 목록 2개 (일기가 전혀 없으면 빈 배열)")


class CalendarEntrySerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(help_text="해당 일기 ID")
    weather = serializers.CharField(help_text="날씨 식별자 (SUNNY, RAINY, CLOUDY 등)")
    primary_emotion = serializers.CharField(help_text="대표 감정 한글명")
    emotion_key = serializers.CharField(help_text="대표 감정 영문 식별자 (스타일링/스티커 파일 매핑용)")
    preview = serializers.CharField(help_text="20자 내외 일기 본문 요약")


class CalendarResponseSerializer(serializers.Serializer):
    has_diaries = serializers.BooleanField(help_text="해당 월에 일기 데이터가 존재하여 캘린더에 감정을 칠할 수 있는지 여부")
    year = serializers.IntegerField(help_text="조회 연도")
    month = serializers.IntegerField(help_text="조회 월")
    calendar_data = serializers.DictField(
        child=CalendarEntrySerializer(),
        help_text="날짜(YYYY-MM-DD)를 Key로 하는 캘린더 감정 정보 해시맵"
    )


class UserFeedbackRequestSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=[('book', '도서'), ('music', '음악'), ('movie', '영화')], help_text="피드백 대상 콘텐츠 종류")
    content_id = serializers.CharField(max_length=50, help_text="콘텐츠 식별자 (도서는 ISBN, 음악은 ID, 영화는 TMDB ID)")
    is_like = serializers.BooleanField(help_text="True: 좋아요, False: 싫어요")


class UserEmotionPreferenceSerializer(serializers.Serializer):
    joy = serializers.FloatField(help_text="선호 기쁨 수치")
    sadness = serializers.FloatField(help_text="선호 슬픔 수치")
    anger = serializers.FloatField(help_text="선호 분노 수치")
    fear = serializers.FloatField(help_text="선호 두려움 수치")
    trust = serializers.FloatField(help_text="선호 신뢰 수치")
    surprise = serializers.FloatField(help_text="선호 놀람 수치")


class UserPreferenceProfileResponseSerializer(serializers.Serializer):
    likes_count = serializers.IntegerField(help_text="누적 좋아요 콘텐츠 개수")
    dislikes_count = serializers.IntegerField(help_text="누적 싫어요 콘텐츠 개수")
    personalization_beta = serializers.FloatField(help_text="현재 추천에 적용되는 개인화 반영 비율 (0.00 ~ 0.40)")
    personalization_level = serializers.CharField(help_text="개인화 취향 반영 단계 설명")
    preferred_emotions = UserEmotionPreferenceSerializer(help_text="좋아요 피드백을 기반으로 산출된 유저의 정서적 선호 프로필 벡터 (피드백이 없으면 null)", allow_null=True)