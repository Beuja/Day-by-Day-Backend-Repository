from rest_framework import serializers
from .models import Diary, DiaryEmotion, DailyRecommended
from daybydaybackend.books.serializers import BookSerializer
from daybydaybackend.music_movie.serializers import MusicResponseSerializer, MovieResponseSerializer

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


class DiaryEmpathyResponseSerializer(serializers.Serializer):
    has_diaries = serializers.BooleanField(help_text="일기 데이터가 존재하여 공감 멘트 생성을 가능한지 여부")
    primary_emotion = serializers.CharField(help_text="유저의 최근 대표 감정 명칭 (슬픔, 기쁨 등)", allow_null=True)
    empathy_message = serializers.CharField(help_text="일기 내용에 감정 매칭 공감 및 추천 유도가 결합된 최종 한글 공감 문장")


class DailyRecommendedSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)
    musics = MusicResponseSerializer(many=True, read_only=True)
    movies = MovieResponseSerializer(many=True, read_only=True)

    class Meta:
        model = DailyRecommended
        fields = ['id', 'mode', 'is_book_fallback', 'books', 'is_music_fallback', 'musics', 'is_movie_fallback', 'movies']