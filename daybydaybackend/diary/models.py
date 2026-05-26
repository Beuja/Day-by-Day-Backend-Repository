from django.db import models
from django.contrib.auth.models import User


class Diary(models.Model):
    WEATHER_CHOICES = [
        ('SUNNY', '맑음'),
        ('CLOUDY', '흐림'),
        ('RAINY', '비'),
        ('SNOWY', '눈'),
        ('WINDY', '바람'),
        ('THUNDER', '천둥'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diaries', default=1)
    content = models.TextField()
    weather = models.CharField(
        max_length=10,
        choices=WEATHER_CHOICES,
        null=True,
        blank=True,
        help_text='일기 작성 당시 날씨'
    )
    image = models.ImageField(
        upload_to='diaries/',
        null=True,
        blank=True,
        help_text='일기에 첨부된 사진'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diary {self.id}"

    class Meta:
        ordering = ['-created_at']



class DiaryEmotion(models.Model):
    diary = models.OneToOneField(Diary, on_delete=models.CASCADE, related_name='emotion')
    joy = models.FloatField(default=0.0, help_text='기쁨 감정 점수 (0.0에서 1.0 사이)')
    sadness = models.FloatField(default=0.0, help_text='슬픔 감정 점수 (0.0에서 1.0 사이)')
    anger = models.FloatField(default=0.0, help_text='분노 감정 점수 (0.0에서 1.0 사이)')
    fear = models.FloatField(default=0.0, help_text='두려움 감정 점수 (0.0에서 1.0 사이)')
    trust = models.FloatField(default=0.0, help_text='신뢰 감정 점수 (0.0에서 1.0 사이)')
    surprise = models.FloatField(default=0.0, help_text='놀람 감정 점수 (0.0에서 1.0 사이)')
    valence = models.FloatField(help_text='감정의 긍정/부정 정도를 나타내는 값 (-1.0에서 1.0 사이)')
    arousal = models.FloatField(help_text='감정의 활성화 정도를 나타내는 값 (-1.0에서 1.0 사이)')
    primary_emotion = models.CharField(max_length=50, help_text='대표 감정 단어', default='알수없음')

    def __str__(self):
        return f"{self.diary.id} - {self.primary_emotion}"

#TODO: 일단 구현해 놓는 데이터 베이스 구조
class DailyRecommended(models.Model):
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name='recommendation')
    music = models.ManyToManyField('music_movie.Music', blank=True, related_name='daily_recommendations')
    movies = models.ManyToManyField('music_movie.Movie', blank=True, related_name='daily_recommendations')
    books = models.ManyToManyField('books.Book', blank=True, related_name='daily_recommendations')
    mode = models.CharField(max_length=20, default='maintain')
    
    class Meta:
        unique_together = ('diary', 'mode')

    def __str__(self):
        return f"Recommendation for Diary {self.diary.id}"