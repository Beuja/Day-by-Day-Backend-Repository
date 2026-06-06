from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

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

class DailyRecommended(models.Model):
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name='recommendation')
    mode = models.CharField(max_length=20, default='maintain', help_text='추천이 생성된 감정 모드')
    musics = models.ManyToManyField('music_movie.Music', blank=True, related_name='daily_recommendations')
    movies = models.ManyToManyField('music_movie.Movie', blank=True, related_name='daily_recommendations')
    books = models.ManyToManyField('books.Book', blank=True, related_name='daily_recommendations')
    is_book_fallback = models.BooleanField(default=False)
    is_music_fallback = models.BooleanField(default=False)
    is_movie_fallback = models.BooleanField(default=False)

    class Meta:
        unique_together = ('diary', 'mode')

    def __str__(self):
        return f"Recommendation for Diary {self.diary.id} ({self.mode})"

class UserFeedback(models.Model):
    FEEDBACK_CHOICES = (
        ('LIKE', 'Like'),
        ('DISLIKE', 'Dislike'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    feedback_type = models.CharField(max_length=7, choices=FEEDBACK_CHOICES)
    
    # Generic Relation을 통해 Book, Music, Movie 통합 지원
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=50)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['user', 'feedback_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.feedback_type} - {self.content_type.model} ({self.object_id})"
