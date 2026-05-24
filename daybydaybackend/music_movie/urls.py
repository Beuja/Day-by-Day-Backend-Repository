from django.urls import path
from . import views

app_name = 'music_movie'

urlpatterns = [
    path('recommend/music/<int:diary_id>/', views.recommend_music_view, name='recommend_music'),
    path('recommend/movie/<int:diary_id>/', views.recommend_movie_view, name='recommend_movie'),
]