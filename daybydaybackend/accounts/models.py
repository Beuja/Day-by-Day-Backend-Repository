# Auth 앱은 Django의 built-in User 모델을 사용하므로 별도의 모델이 필요하지 않습니다.
# from django.contrib.auth.models import User를 사용합니다.

from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    # User 모델과 1:1 관계 정립
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    
    # 추가하고 싶은 속성 정의
    emotion_variance = models.FloatField(default=0.05, help_text="유저의 누적 정서 분산도")

    def __str__(self):
        return f"{self.user.username}의 프로필"