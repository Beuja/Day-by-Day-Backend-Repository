from django.urls import path, include
from daybydaybackend.diary import views as diary_views

urlpatterns = [
    # 인증 관련 API
    path('auth/', include('daybydaybackend.accounts.urls')),

    # 일기 관련 API
    path('diary/', include('daybydaybackend.diary.urls')),

    # [리팩토링] 추천 관련 가상 API 네임스페이스 (디렉토리 독립성 보존)
    # 1. 메인 화면 통합 개인화 추천
    path('recommend/main/', diary_views.get_main_recommendations, name='get_main_recommendations'),
    # 2. 도서 추천
    path('', include('daybydaybackend.books.urls')),

    # 음악/영화 추천 API
    path('recommend/', include('daybydaybackend.music_movie.urls')),
]