# books/models.py
from django.db import models

class BookManager(models.Manager):
    def get_by_natural_key(self, isbn):
        return self.get(isbn=isbn)

class Book(models.Model):
    # ISBN을 기본키로 사용
    isbn = models.CharField(max_length=13, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField()
    link = models.URLField(null=True, blank=True)
    is_review_crawled = models.BooleanField(default=False)
    cover_url = models.URLField(null=True, blank=True)
    
    # 2차원 감정 벡터
    valence = models.FloatField(null=True, blank=True)
    arousal = models.FloatField(null=True, blank=True)
    
    # 6차원 감정 벡터
    joy = models.FloatField(null=True, blank=True)
    sadness = models.FloatField(null=True, blank=True)
    anger = models.FloatField(null=True, blank=True)
    fear = models.FloatField(null=True, blank=True)
    trust = models.FloatField(null=True, blank=True)
    surprise = models.FloatField(null=True, blank=True)

    def natural_key(self):
        return (self.isbn,)
    
    class Meta:
        ordering = ['-title']

    