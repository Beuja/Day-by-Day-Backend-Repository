from django.urls import path
from . import views

urlpatterns = [
    # 회원 가입 API
    path('auth/register/', views.register, name='register'),

    # 로그인 API
    path('auth/login/', views.login, name='login'),

    # 로그아웃 API
    path('auth/logout/', views.logout, name='logout'),

    # 사용자 정보 관리 API (GET: 조회, PATCH: 수정, DELETE: 탈퇴)
    path('users/', views.manage_user, name='manage_user'),

    # 일기를 ai 한테 보내는 API (Diary + Gemini API 기반 감정 추출)
    path('diary/send/', views.analyze_diary_emotion, name='analyze_diary_emotion'),
]