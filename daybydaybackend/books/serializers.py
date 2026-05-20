from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ['isbn', 'title', 'author', 'category', 'description', 'valence', 'arousal']

    def get_description(self, obj):
        if obj.description and len(obj.description) > 100:
            return obj.description[:100] + '...'
        return obj.description

class RecommendRequestSerializer(serializers.Serializer):
    diary_id = serializers.IntegerField(required=True, help_text="분석된 일기 ID")
    mode = serializers.ChoiceField(choices=['maintain', 'reverse', 'boost'], default='maintain')
    count = serializers.IntegerField(default=3, min_value=1)