from django.urls import path
from . import views

app_name = 'music_movie'

urlpatterns = [
    # 감정 기반 콘텐츠(음악/영화) 추천 API
    path('recommend/', views.recommend_content, name='recommend_content'),
]
