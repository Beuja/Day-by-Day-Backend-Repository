from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.db import transaction

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView

from .models import Diary, DiaryEmotion
from .serializers import DiarySerializer
from .services import analyze_emotion_with_gemini

# ===== 회원가입 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="회원가입",
    operation_description="새로운 사용자를 등록하고 즉시 로그인 상태(토큰 발급)로 만듭니다.",

    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 아이디'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='비밀번호'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='이메일 주소 (선택)'),
        },
        required=['username', 'password']
    ),

    responses={
        201: openapi.Response('회원가입 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 고유 ID'),
                'token': openapi.Schema(type=openapi.TYPE_STRING, description='인증 토큰'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름')
            }
        )),
        400: '잘못된 요청 (입력값 누락 또는 중복된 아이디)'
    }
)
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
        required=['username', 'password']
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
    operation_description="현재 로그아웃 처리합니다.",
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
@permission_classes([AllowAny])
def logout(request):
    # 단순 프로젝트용이므로 토큰 검증 없이 바로 성공 메시지 리턴 또는 토큰 삭제
    if request.user and request.user.is_authenticated:
        request.user.auth_token.delete()
    return Response(
        {'message': '로그아웃 되었습니다.'},
        status=status.HTTP_200_OK
    )

#==== 사용자 정보 조회 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="사용자 정보 조회",
    operation_description="사용자의 정보를 조회합니다.",
    responses={
        200: openapi.Response('조회 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 고유 ID'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자 이름'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='이메일 주소'),
            }
        )),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def user_info(request):
    user = request.user
    if user.is_authenticated:
        return Response(
            {'id': user.id, 'username': user.username, 'email': user.email},
            status=status.HTTP_200_OK
        )
    return Response(
        {'id': 1, 'username': 'test_user (인증 없음)', 'email': 'test@example.com'},
        status=status.HTTP_200_OK
    )

# ===== 일기 분석 API (저장된 일기 가져오기 기반) =====
@swagger_auto_schema(
    method='post',
    operation_summary="일기 감정 분석",
    operation_description="저장되어 있는 일기 ID를 받아와 Gemini API로 감정을 분석하고 결과를 DB에 저장/업데이트 합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'diary_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='분석할 일기의 ID'),
        },
        required=['diary_id']
    ),
    responses={
        200: openapi.Response('감정 분석 성공', DiarySerializer),
        404: '일기를 찾을 수 없음'
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])  # 토큰 인증해야 함
@transaction.atomic # 비즈니스 로직 도중 실패 시 DB 롤백 보장
def create_diary(request):
    # 원래 create_diary 였지만 흐름이 변경되어 감정 분석 로직으로 쓰입니다. (원한다면 analyze_diary_emotion으로 이름 변경 가능)
    diary_id = request.data.get('diary_id')
    if not diary_id:
        return Response({'message': '분석할 일기의 ID를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        # 1. DB에서 해당 ID의 일기 객체를 찾아옵니다. (테스트 편의를 위해 유저 검증 생략)
        diary = Diary.objects.get(id=diary_id)
    except Diary.DoesNotExist:
        return Response({'message': '해당 일기를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    
    # 2. 서비스 레이어(Gemini API) 호출하여 일기 내용을 기반으로 감정 분석을 수행합니다.
    emotion_dict = analyze_emotion_with_gemini(diary.content)
    
    # 3. 감정 데이터 저장 (DB) 
    # update_or_create: 만약 이미 해당 일기에 감정(Emotion) 데이터가 있다면 업데이트, 없다면 새로 생성합니다. 
    DiaryEmotion.objects.update_or_create(
        diary=diary,
        defaults={
            'valence': emotion_dict.get('valence', 0.0),
            'arousal': emotion_dict.get('arousal', 0.0),
            'primary_emotion': emotion_dict.get('primary_emotion', '알수없음')
        }
    )
    
    # 4. 저장된 전체 데이터(Diary + 하위의 Emotion까지) Serialize 하여 반환
    # 이제 diary.emotion을 통해 방금 분석된 감정결과도 같이 응답(JSON)에 묶여 내려갑니다.
    serializer = DiarySerializer(diary)
    return Response(serializer.data, status=status.HTTP_200_OK)

# ===== 일기 전송 API ===== 으로 되어 있지만 이제 db에 저장된 감정 분석 결과를 가져오는 API로 바꿔야함
# @swagger_auto_schema(
#     method='post',
#     operation_summary="일기 전송",
#     operation_description="사용자가 작성한 일기를 AI에게 전송합니다.",
#     request_body=openapi.Schema(
#         type=openapi.TYPE_OBJECT,
#         properties={
#             'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 고유 ID'),
#             'diary_content': openapi.Schema(type=openapi.TYPE_STRING, description='일기 내용'),
#         },
#         required=['user_id', 'diary_content']
#     ),
#     responses={
#         200: openapi.Response('일기 전송 성공', openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'message': openapi.Schema(type=openapi.TYPE_STRING, description='일기 전송 완료 메시지'),
#             }
#         )),
#         400: '잘못된 요청 (입력값 누락)'
#     }
# )
# @api_view(['GET'])
# @permission_classes([AllowAny])
# def send_diary(request):
#     user_id = request.data.get('user_id')
#     diary_content = request.data.get('diary_content')

#     if not user_id or not diary_content:
#         return Response(
#             {'message': '사용자 ID와 일기 내용을 입력해주세요.'},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # 실제로는 AI에게 일기를 전송하는 로직이 여기에 들어가야 합니다.
#     # 예시에서는 단순히 성공 메시지만 반환합니다.

#     return Response(
#         {'message': '일기가 AI에게 성공적으로 전송되었습니다.'},
#         status=status.HTTP_200_OK
#     )