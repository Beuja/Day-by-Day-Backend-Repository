from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Diary, DiaryEmotion

class DiaryEmotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiaryEmotion
        fields = ['valence', 'arousal', 'primary_emotion']

class DiarySerializer(serializers.ModelSerializer):
    emotion = DiaryEmotionSerializer(read_only=True)

    class Meta:
        model = Diary
        fields = ['id', 'content', 'created_at', 'emotion']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']  # 비밀번호는 제외 (보안상)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class DiarySerializer(serializers.Serializer):
    content = serializers.CharField()
    user_id = serializers.IntegerField()
