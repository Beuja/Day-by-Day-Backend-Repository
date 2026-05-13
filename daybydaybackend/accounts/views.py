from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    RegisterSerializer, LoginSerializer, 
    UserSerializer, UserUpdateSerializer
)
from . import services


# ===== 회원가입 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="회원가입",
    operation_description="새로운 사용자를 등록하고 즉시 로그인 상태(토큰 발급)로 만듭니다.",
    request_body=RegisterSerializer,
    responses={
        201: openapi.Response('회원가입 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 고유 ID'),
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='인증 토큰'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름')
            }
        )),
        400: '잘못된 요청'
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # 비즈니스 로직(서비스)을 호출하여 유저 생성 및 토큰 발급
    user, token = services.create_user_account(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password'],
        email=serializer.validated_data.get('email', '')
    )

    return Response(
        {'id': user.id, 'token': token.key, 'username': user.username},
        status=status.HTTP_201_CREATED
    )


# ===== 로그인 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="로그인",
    operation_description="아이디와 비밀번호를 사용하여 로그인합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 아이디'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='비밀번호')
        },
        required=['username', 'password'],
        example={
            "username": "testuser",
            "password": "testpassword123"
        }
    ),
    responses={
        200: openapi.Response('로그인 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 고유 ID'),
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='인증 토큰'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름')
            }
        )),
        401: '인증 실패'
    }
)
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
        {'id': user.id, 'token': token.key, 'username': user.username},
        status=status.HTTP_200_OK
    )


# ===== 로그아웃 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="로그아웃",
    operation_description="현재 사용자를 로그아웃 처리하고 토큰을 삭제합니다.",
    security=[{'Token': []}],  # Swagger 자물쇠 아이콘 연동
    responses={
        200: openapi.Response('로그아웃 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='로그아웃 완료 메시지'),
            }
        )),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])  # 토큰 기반 인증 사용
@permission_classes([IsAuthenticated])          # 로그인된 사용자만 접근 가능
def logout(request):
    # 로그인된 사용자의 토큰을 삭제하여 더 이상 인증 불가 상태로 만듦
    request.user.auth_token.delete()
    return Response(
        {'message': '로그아웃 되었습니다.'},
        status=status.HTTP_200_OK
    )


# ==== 사용자 정보 조회, 수정 및 탈퇴 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="사용자 정보 조회",
    operation_description="토큰을 기반으로 현재 접속 중인 사용자의 정보를 조회합니다.",
    security=[{'Token': []}],
    responses={
        200: openapi.Response('조회 성공', UserSerializer),
        401: '인증되지 않은 사용자'
    }
)
@swagger_auto_schema(
    method='patch',
    operation_summary="회원 정보 수정",
    operation_description="현재 로그인된 사용자의 정보(이메일, 비밀번호)를 수정합니다.",
    security=[{'Token': []}],
    request_body=UserUpdateSerializer,
    responses={
        200: openapi.Response('수정 성공', UserSerializer),
        400: '잘못된 요청',
        401: '인증되지 않은 사용자'
    }
)
@swagger_auto_schema(
    method='delete',
    operation_summary="회원 탈퇴",
    operation_description="현재 로그인된 사용자의 계정을 삭제합니다. 이 작업은 되돌릴 수 없습니다.",
    security=[{'Token': []}],
    responses={
        204: '회원 탈퇴 성공',
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET', 'PATCH', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def manage_user(request):
    user = request.user

    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 비즈니스 로직(서비스)을 호출하여 유저 정보 업데이트
        updated_user = services.update_user_account(
            user=user,
            email=serializer.validated_data.get('email'),
            password=serializer.validated_data.get('password')
        )
        return Response(UserSerializer(updated_user).data, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        user.delete()
        return Response({'message': '계정이 성공적으로 삭제되었습니다.'}, status=status.HTTP_204_NO_CONTENT)
