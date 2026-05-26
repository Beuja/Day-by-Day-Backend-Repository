# music_movie/serializers.py
from rest_framework import serializers

class ContentRecommendationRequestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=[
            ('maintain', 'Maintain (감정 유지)'),
            ('shift', 'Shift (감정 전환)'),
            ('amplification', 'Amplification (감정 극대화)'),
        ],
        default='maintain',
        required=False,
        help_text="감정 추천 전략 모드: maintain (현재 감정 유지), shift (반대 감정으로 전환), amplification (현재 감정 극대화)"
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
        if hasattr(obj, 'id'): return obj.id
        return obj.get('track_id') if isinstance(obj, dict) else None

    def get_artist(self, obj):
        if hasattr(obj, 'artist'): return obj.artist if obj.artist else ''
        return obj.get('artist', '') if isinstance(obj, dict) else ''

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
        if hasattr(obj, 'director'): return obj.director if obj.director else ''
        return obj.get('director', '') if isinstance(obj, dict) else ''

    def get_image_url(self, obj):
        if hasattr(obj, 'poster_path'): return obj.poster_path if obj.poster_path else ''
        return obj.get('image_url', '') if isinstance(obj, dict) else ''

    def get_tags(self, obj):
        if hasattr(obj, 'genre'): return [obj.genre] if obj.genre else []
        return obj.get('tags', []) if isinstance(obj, dict) else []

    def get_score(self, obj):
        if hasattr(obj, 'score'): return obj.score
        return obj.get('score', 0.0) if isinstance(obj, dict) else 0.0