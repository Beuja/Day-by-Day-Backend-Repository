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
    track_id = serializers.IntegerField()
    title = serializers.CharField()
    artist = serializers.CharField(allow_blank=True, required=False, default='')
    image_url = serializers.URLField(allow_blank=True, required=False, default='')
    tags = serializers.ListField(child=serializers.CharField(), default=list)
    score = serializers.FloatField(required=False, default=0.0)

class MovieResponseSerializer(serializers.Serializer):
    movie_id = serializers.IntegerField()
    title = serializers.CharField()
    director = serializers.CharField(allow_blank=True, required=False, default='')
    image_url = serializers.URLField(allow_blank=True, required=False, default='')
    tags = serializers.ListField(child=serializers.CharField(), default=list)
    score = serializers.FloatField(required=False, default=0.0)