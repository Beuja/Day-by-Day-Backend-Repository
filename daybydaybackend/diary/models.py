from django.db import models
from django.contrib.auth.models import User


class Diary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diaries', null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diary {self.id}"

    class Meta:
        ordering = ['-created_at']


class DiaryEmotion(models.Model):
    diary = models.OneToOneField(Diary, on_delete=models.CASCADE, related_name='emotion')
    valence = models.FloatField(help_text='감정의 긍정/부정 정도를 나타내는 값 (-1.0에서 1.0 사이)')
    arousal = models.FloatField(help_text='감정의 활성화 정도를 나타내는 값 (-1.0에서 1.0 사이)')
    primary_emotion = models.CharField(max_length=50, help_text='대표 감정 단어', default='알수없음')

    def __str__(self):
        return f"{self.diary.id} - {self.primary_emotion}"
