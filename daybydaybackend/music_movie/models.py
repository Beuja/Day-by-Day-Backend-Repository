from django.db import models
import json


class Music(models.Model):
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, null=True, blank=True)
    source_tag = models.CharField(max_length=100, null=True, blank=True)
    listeners = models.IntegerField(default=0)
    playcount = models.IntegerField(default=0)
    
    # 태그들을 JSON으로 저장
    tags = models.JSONField(default=list)
    
    # 10차원 감정 벡터
    emotion_vector = models.JSONField(default=dict)
    
    # Russell의 2차원 감정 벡터 (캐시)
    valence = models.FloatField(null=True, blank=True)
    arousal = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.artist}"
    
    class Meta:
        ordering = ['-playcount']


class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=100, null=True, blank=True)
    overview = models.TextField(blank=True)
    
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.IntegerField(default=0)
    popularity = models.FloatField(default=0.0)
    
    release_date = models.DateField(null=True, blank=True)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    
    # Russell의 2차원 감정 벡터
    valence = models.FloatField(null=True, blank=True)
    arousal = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-popularity']
