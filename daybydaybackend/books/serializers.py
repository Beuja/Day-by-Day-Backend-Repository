from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class RecommendRequestSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField()
    emotion = serializers.DictField(
        child=serializers.FloatField(min_value=0.0, max_value=1.0),
        help_text='사용자 감정 벡터 (joy, sadness, anger, fear, trust, surprise)'
    )
    mode = serializers.ChoiceField(choices=['maintain', 'shift', 'amplification'], default='maintain')
    count = serializers.IntegerField(default=3, min_value=1)