from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # 회원 가입 API
    path('register/', views.register, name='register'),

    # 로그인 API
    path('login/', views.login, name='login'),

    # 로그아웃 API
    path('logout/', views.logout, name='logout'),

    # 사용자 정보 관리 API (GET: 조회, PATCH: 수정, DELETE: 탈퇴)
    path('users/', views.manage_user, name='manage_user'),
]
