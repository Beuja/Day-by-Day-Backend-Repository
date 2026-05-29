from rest_framework import serializers
from daybydaybackend.diary.models import DailyRecommended

class ContentRecommendationRequestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=[
            ('maintain', 'Maintain (감정 유지)'),
            ('shift', 'Shift (감정 전환)'),
            ('amplification', 'Amplification (감정 극대화)'),
            ('auto', 'Auto (감정 분석 기반 자동 결정)'),
        ],
        default='auto',
        required=False,
        help_text="감정 추천 전략 모드: maintain (현재 감정 유지), shift (반대 감정으로 전환), amplification (현재 감정 극대화), auto (자동 결정)"
    )
    count = serializers.IntegerField(default=3, min_value=1, max_value=20, required=False)

class MusicResponseSerializer(serializers.Serializer):
    track_id = serializers.SerializerMethodField()
    title = serializers.CharField()
    artist = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    def get_track_id(self, obj):
        # 💡 [500 에러 해결] 객체면 id를, 딕셔너리이면 track_id를 유연하게 뽑아냅니다.
        if hasattr(obj, 'id'): return obj.id
        return obj.get('track_id') if isinstance(obj, dict) else None

    def get_artist(self, obj):
        val = getattr(obj, 'artist', '') if not isinstance(obj, dict) else obj.get('artist', '')
        return val if val else '아티스트 미상'

    def get_image_url(self, obj):
        if hasattr(obj, 'image_url'): return obj.image_url if obj.image_url else ''
        return obj.get('image_url', '') if isinstance(obj, dict) else ''

    def get_tags(self, obj):
        if hasattr(obj, 'tags'): return obj.tags if isinstance(obj.tags, list) else []
        return obj.get('tags', []) if isinstance(obj, dict) else []

    def get_score(self, obj):
        if hasattr(obj, 'score'): return obj.score
        return obj.get('score', 0.0) if isinstance(obj, dict) else 0.0


class MovieResponseSerializer(serializers.Serializer):
    movie_id = serializers.SerializerMethodField()
    title = serializers.CharField()
    director = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    def get_movie_id(self, obj):
        if hasattr(obj, 'tmdb_id'): return obj.tmdb_id
        return obj.get('movie_id') if isinstance(obj, dict) else None

    def get_director(self, obj):
        # 💡 [공백 해결] DB에 값이 아예 없거나, ""(빈 문자열)인 경우를 모두 잡아냅니다.
        val = getattr(obj, 'director', '') if not isinstance(obj, dict) else obj.get('director', '')
        return val if val else '감독 정보 없음'

    def get_image_url(self, obj):
        if hasattr(obj, 'poster_path'): return obj.poster_path if obj.poster_path else ''
        return obj.get('image_url', '') if isinstance(obj, dict) else ''

    def get_tags(self, obj):
        if hasattr(obj, 'genre'): return [obj.genre] if obj.genre else []
        return obj.get('tags', []) if isinstance(obj, dict) else []

    def get_score(self, obj):
        if hasattr(obj, 'score'): return obj.score
        return obj.get('score', 0.0) if isinstance(obj, dict) else 0.0


class MusicDailyRecommendedSerializer(serializers.ModelSerializer):
    musics = MusicResponseSerializer(many=True, read_only=True)

    class Meta:
        model = DailyRecommended
        fields = ['mode', 'musics']

class MovieDailyRecommendedSerializer(serializers.ModelSerializer):
    movies = MovieResponseSerializer(many=True, read_only=True)

    class Meta:
        model = DailyRecommended
        fields = ['mode', 'movies']