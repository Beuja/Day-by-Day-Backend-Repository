from django.urls import path, include
from daybydaybackend.diary import views as diary_views

urlpatterns = [
    # 인증 관련 API
    path('auth/', include('daybydaybackend.accounts.urls')),

    # 일기 관련 API
    path('diary/', include('daybydaybackend.diary.urls')),

    # 1. 메인 화면 통합 개인화 추천 (프론트 하위 호환 유지)
    path('recommend/main/', diary_views.get_main_recommendations, name='get_main_recommendations'),

    # [리팩토링] 유저 정서 취향 피드백 전용 네임스페이스 (신설 독립 격리)
    path('preference/feedback/', diary_views.register_feedback, name='register_feedback'),
    path('preference/profile/', diary_views.get_user_preference_profile, name='get_user_preference_profile'),

    # 3. 도서 추천
    path('', include('daybydaybackend.books.urls')),

    # 음악/영화 추천 API
    path('recommend/', include('daybydaybackend.music_movie.urls')),
]