from rest_framework import serializers
from .models import Music, Movie


class MusicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Music
        fields = ['id', 'title', 'artist', 'source_tag', 'listeners', 'playcount', 'tags', 'valence', 'arousal']


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ['tmdb_id', 'title', 'genre', 'overview', 'vote_average', 'vote_count', 
                  'popularity', 'release_date', 'poster_path', 'valence', 'arousal']


class RecommendationRequestSerializer(serializers.Serializer):
    """추천 요청용 시리얼라이저"""
    valence = serializers.FloatField(min_value=-1.0, max_value=1.0)
    arousal = serializers.FloatField(min_value=-1.0, max_value=1.0)
    content_type = serializers.ChoiceField(choices=['music', 'movie', 'both'])
    mode = serializers.ChoiceField(
        choices=['maintain', 'shift', 'amplify', 'release', 'energize'],
        default='maintain'
    )
    count = serializers.IntegerField(default=5, min_value=1, max_value=20)
