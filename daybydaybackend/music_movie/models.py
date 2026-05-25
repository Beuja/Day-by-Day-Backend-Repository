from django.db import models

class Music(models.Model):
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, null=True, blank=True)
    source_tag = models.CharField(max_length=100, null=True, blank=True)
    listeners = models.IntegerField(default=0)
    playcount = models.IntegerField(default=0)
    
    # 프론트엔드 반환 및 캐싱 복원을 위한 자켓 이미지 주소 열
    image_url = models.URLField(max_length=500, null=True, blank=True)
    
    # 태그들을 JSON으로 저장
    tags = models.JSONField(default=list)
    
    # [필수 추가] Books 모델 스펙에 맞춘 개별 감정 컬럼 분리 구축
    joy = models.FloatField(default=0.0, null=True, blank=True)
    sadness = models.FloatField(default=0.0, null=True, blank=True)
    anger = models.FloatField(default=0.0, null=True, blank=True)
    fear = models.FloatField(default=0.0, null=True, blank=True)
    trust = models.FloatField(default=0.0, null=True, blank=True)
    surprise = models.FloatField(default=0.0, null=True, blank=True)
    
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
    director = models.CharField(max_length=255, null=True, blank=True)
    genre = models.CharField(max_length=100, null=True, blank=True)
    overview = models.TextField(blank=True)
    
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.IntegerField(default=0)
    popularity = models.FloatField(default=0.0)
    
    release_date = models.DateField(null=True, blank=True)
    
    # [필수 추가] load_content_data가 찾는 포스터 이미지 경로 컬럼
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    
    # [필수 추가] Books 모델 스펙에 맞춘 개별 감정 컬럼 분리 구축
    joy = models.FloatField(default=0.0, null=True, blank=True)
    sadness = models.FloatField(default=0.0, null=True, blank=True)
    anger = models.FloatField(default=0.0, null=True, blank=True)
    fear = models.FloatField(default=0.0, null=True, blank=True)
    trust = models.FloatField(default=0.0, null=True, blank=True)
    surprise = models.FloatField(default=0.0, null=True, blank=True)
    
    # Russell의 2차원 감정 벡터
    valence = models.FloatField(null=True, blank=True)
    arousal = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-popularity']