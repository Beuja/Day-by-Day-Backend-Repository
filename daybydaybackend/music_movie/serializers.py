from rest_framework import serializers

class ContentRecommendationRequestSerializer(serializers.Serializer):
    mode = serializers.CharField(default='maintain', required=False)
    count = serializers.IntegerField(default=3, min_value=1, max_value=20, required=False)

class MusicResponseSerializer(serializers.Serializer):
    track_id = serializers.IntegerField()
    title = serializers.CharField()
    artist = serializers.CharField(allow_blank=True, required=False, default='')
    image_url = serializers.URLField(allow_blank=True, required=False, default='')
    tags = serializers.ListField(child=serializers.CharField(), default=list)

class MovieResponseSerializer(serializers.Serializer):
    movie_id = serializers.IntegerField()
    title = serializers.CharField()
    director = serializers.CharField(allow_blank=True, required=False, default='')
    image_url = serializers.CharField(allow_blank=True, required=False, default='')
    tags = serializers.ListField(child=serializers.CharField(), default=list)