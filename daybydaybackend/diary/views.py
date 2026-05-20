from django.db import transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Diary
from .serializers import (
    DiarySerializer, AnalyzeEmotionRequestSerializer,
    DiaryCreateRequestSerializer
)
from . import services


# ===== 일기 작성 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="일기 작성",
    operation_description="사용자가 일기를 작성하여 DB에 저장합니다.",
    security=[{'Token': []}],
    request_body=DiaryCreateRequestSerializer,
    responses={
        201: openapi.Response('일기 작성 성공', DiarySerializer),
        400: '잘못된 요청',
        401: '인증되지 않은 사용자'
    }
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_diary(request):
    serializer = DiaryCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # 생성 로직은 services 로 분리
    diary = services.create_diary_entry(user=request.user, content=serializer.validated_data['content'])
    
    # 응답용 시리얼라이저로 래핑 (ID와 함께 반환)
    response_serializer = DiarySerializer(diary)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


# ===== 일기 감정 분석 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="일기 감정 분석",
    operation_description="저장되어 있는 일기 ID를 받아와 감정을 분석하고 결과를 DB에 저장/업데이트 합니다.",
    security=[{'Token': []}],  # Swagger 자물쇠 아이콘 연동
    request_body=AnalyzeEmotionRequestSerializer,
    responses={
        200: openapi.Response('감정 분석 성공', DiarySerializer),
        404: '일기를 찾을 수 없거나 접근 권한 없음'
    }
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic  # 비즈니스 로직 도중 실패 시 DB 롤백 보장
def analyze_diary_emotion(request):
    serializer = AnalyzeEmotionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    diary_id = serializer.validated_data['diary_id']
        
    try:
        # 비즈니스 로직(서비스)으로 모두 이관
        diary = services.process_diary_emotion(diary_id=diary_id, user=request.user)
    except Diary.DoesNotExist:
        return Response({'message': '해당 일기를 찾을 수 없거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    
    # 분석 결과(하위 Emotion 포함)를 직렬화하여 반환
    serializer = DiarySerializer(diary)
    return Response(serializer.data, status=status.HTTP_200_OK)
