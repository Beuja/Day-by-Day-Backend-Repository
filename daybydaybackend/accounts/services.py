from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


# ===== 유저 관련 비즈니스 로직 =====
def create_user_account(username, password, email=''):
    """새로운 사용자 계정을 생성하고 토큰을 발급하는 비즈니스 로직"""
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def update_user_account(user, email=None, password=None):
    """기존 사용자의 정보를 안전하게 수정하는 비즈니스 로직"""
    if email is not None:
        user.email = email
        
    if password is not None:
        user.set_password(password)  # 비밀번호는 반드시 해시화하여 저장
        
    user.save()
    return user
