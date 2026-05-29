from django.urls import path, include
from daybydaybackend.diary import views as diary_views

urlpatterns = [
    # 인증 관련 API
    path('auth/', include('daybydaybackend.accounts.urls')),

    # 일기 관련 API
    path('diary/', include('daybydaybackend.diary.urls')),

    # 1. 메인 화면 통합 개인화 추천 (프론트 하위 호환 유지)
    path('recommend/main/', diary_views.get_main_recommendations, name='get_main_recommendations'),



    # 3. 도서 추천
    path('', include('daybydaybackend.books.urls')),

    # 음악/영화 추천 API
    path('recommend/', include('daybydaybackend.music_movie.urls')),
]