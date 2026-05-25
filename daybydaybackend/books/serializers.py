from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class ContentRecommendationRequestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['maintain', 'shift', 'amplification'], default='maintain')
    count = serializers.IntegerField(default=3, min_value=1)

    class Meta:
        ref_name = 'BooksContentRecommendationRequestSerializer'


class BookRecommendationPathSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(help_text='추천 대상 일기 ID')

    class Meta:
        ref_name = 'BookRecommendationPathSerializer'