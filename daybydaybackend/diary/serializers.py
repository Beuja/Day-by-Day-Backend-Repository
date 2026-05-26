from rest_framework import serializers
from .models import Diary, DiaryEmotion
from daybydaybackend.music_movie.models import Movie, Music
from daybydaybackend.books.serializers import BookSerializer

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
        model = Movie
        fields = '__all__'
        ref_name = 'DiaryMovieSerializer'  # 👈 drf-yasg 중복 식별 오류 해결

class MusicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Music
        fields = '__all__'
        ref_name = 'DiaryMusicSerializer'  # 👈 drf-yasg 중복 식별 오류 해결

class MainRecommendationResponseSerializer(serializers.Serializer):
    has_diaries = serializers.BooleanField(help_text="해당 유저의 최근 일기 작성 데이터가 존재하여 추천이 가능한지 여부")
    emotion_status = DiaryEmotionSerializer(help_text="최근 5개 일기의 Plutchik 6대 감정 평균 수치 (일기가 전혀 없으면 null)", allow_null=True)
    books = BookSerializer(many=True, help_text="맞춤형 추천 도서 목록 2개 (일기가 전혀 없으면 빈 배열)")
    music = MusicSerializer(many=True, help_text="맞춤형 추천 음악 목록 2개 (일기가 전혀 없으면 빈 배열)")
    movies = MovieSerializer(many=True, help_text="맞춤형 추천 영화 목록 2개 (일기가 전혀 없으면 빈 배열)")

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
