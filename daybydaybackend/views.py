from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status


# ===== 회원가입 API =====
@api_view(['POST'])
@permission_classes([AllowAny])  # 누구나 접근 가능
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')

    # 입력값 검증
    if not username or not password:
        return Response(
            {'message': '아이디와 비밀번호를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 아이디 중복 체크
    if User.objects.filter(username=username).exists():
        return Response(
            {'message': '이미 존재하는 아이디입니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 사용자 생성 (create_user는 비밀번호를 자동으로 암호화)
    user = User.objects.create_user(username=username, password=password)

    # 토큰 자동 발급 (가입 즉시 로그인 상태로 만들기 위해)
    token = Token.objects.create(user=user)

    return Response(
        {'token': token.key, 'username': user.username},
        status=status.HTTP_201_CREATED
    )


# ===== 로그인 API =====
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    # authenticate: 아이디/비밀번호가 맞으면 user 객체, 틀리면 None 반환
    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {'message': '아이디 또는 비밀번호가 올바르지 않습니다.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # 기존 토큰 가져오거나 새로 만들기
    token, created = Token.objects.get_or_create(user=user)

    return Response(
        {'token': token.key, 'username': user.username},
        status=status.HTTP_200_OK
    )


# ===== 로그아웃 API =====
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  # 로그인된 사용자만 접근 가능
def logout(request):
    # 해당 사용자의 토큰을 삭제 → 더 이상 인증 불가
    request.user.auth_token.delete()
    return Response(
        {'message': '로그아웃 되었습니다.'},
        status=status.HTTP_200_OK
    )