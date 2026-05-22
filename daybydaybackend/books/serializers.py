from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__'

class RecommendRequestSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(help_text='추천을 요청하는 일기의 ID')
    emotion = serializers.DictField(
        child=serializers.FloatField(min_value=-1.0, max_value=1.0),
        help_text='사용자 감정 벡터 (joy, sadness, anger, fear, trust, surprise)'
    )
    mode = serializers.ChoiceField(choices=['maintain', 'shift', 'amplification'], default='maintain')
    count = serializers.IntegerField(default=3, min_value=1)

    class Meta:
        swagger_schema_fields = {
            "example": {
                "diary_id": 1,
                "emotion": {
                    "joy": 0.7,
                    "sadness": 0.2,
                    "anger": 0.1,
                    "fear": 0.0,
                    "trust": 0.5,
                    "surprise": 0.3,
                    "valence": 0.5,
                    "arousal": -0.2,
                    "primary_emotion": "joy"
                },
                "mode": "shift",
                "count": 5
            }
        }

