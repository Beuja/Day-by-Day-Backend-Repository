from rest_framework import serializers
from .models import Book
from daybydaybackend.diary.models import DailyRecommended

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class DailyRecommendedSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)

    class Meta:
        model = DailyRecommended
        fields = ['mode', 'books']
        
class ContentRecommendationRequestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['maintain', 'shift', 'amplification', 'auto'], default='auto')
    count = serializers.IntegerField(default=3, min_value=1)

    class Meta:
        ref_name = 'BooksContentRecommendationRequestSerializer'


class BookRecommendationPathSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(help_text='추천 대상 일기 ID')

    class Meta:
        ref_name = 'BookRecommendationPathSerializer'