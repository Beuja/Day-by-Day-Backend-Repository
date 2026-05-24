from django.urls import path
from . import views

app_name = 'music_movie'

urlpatterns = [
    # 감정 기반 음악 추천 API
    path('music/<int:diary_id>/', views.recommend_music_view, name='recommend_music'),

    # 감정 기반 영화 추천 API
    path('movie/<int:diary_id>/', views.recommend_movie_view, name='recommend_movie'),
]
