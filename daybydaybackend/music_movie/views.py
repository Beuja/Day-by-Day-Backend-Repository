# pyright: reportMissingImports=false
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from daybydaybackend.diary.models import Diary, DailyRecommended
from . import serializers
from . import services
from .serializers import MusicDailyRecommendedSerializer, MovieDailyRecommendedSerializer

music_recommendation_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='추천 전략'),
        'recommendations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT),
            description='추천된 음악 목록',
        ),
    },
)

movie_recommendation_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='추천 전략'),
        'recommendations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT),
            description='추천된 영화 목록',
        ),
    },
)


@swagger_auto_schema(
    method='get',
    operation_summary='저장된 음악 추천 조회',
    operation_description='일기 상세에 저장된 음악 추천 결과를 복원해서 반환합니다. 현재는 6차원 감정 벡터 기반 추천이 기본이며, 하위 호환용 2D(valence/arousal) 추천 로직도 서비스 계층에 함께 존재합니다.',
    responses={200: openapi.Response('조회 성공', music_recommendation_response_schema)},
)
@swagger_auto_schema(
    method='post',
    operation_summary='감정 기반 음악 추천 생성',
    operation_description='일기의 6차원 감정 벡터를 기반으로 음악 추천 결과를 생성합니다. 요청 바디의 mode 파라미터를 통해 세 가지 추천 전략 중 하나를 사용할 수 있습니다.\n\n- maintain: 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 음악을 추천합니다 (기본값).\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 밝은 감정으로 전환(Shift)할 수 있는 음악을 추천합니다.\n- amplification: 현재의 신나고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 신나는 음악을 추천합니다.',
    request_body=serializers.ContentRecommendationRequestSerializer,
    responses={200: openapi.Response('생성 성공', music_recommendation_response_schema)},
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_music_view(request, diary_id):
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)
    
    if request.method == 'GET':
        data = services.get_saved_music_metadata(diary_obj)
        serializer = MusicDailyRecommendedSerializer(data, many=True)
        return Response({"recommendations": serializer.data}, status=status.HTTP_200_OK)
        
    if request.method == 'POST':
        req_serializer = serializers.ContentRecommendationRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        mode = req_serializer.validated_data.get('mode', 'maintain')
        count = req_serializer.validated_data.get('count', 3)
        
        raw_emotion = getattr(diary_obj, 'emotion', None)
        user_6d_emotion = {
            'joy': getattr(raw_emotion, 'joy', 0.0),
            'sadness': getattr(raw_emotion, 'sadness', 0.0),
            'anger': getattr(raw_emotion, 'anger', 0.0),
            'fear': getattr(raw_emotion, 'fear', 0.0),
            'trust': getattr(raw_emotion, 'trust', 0.0),
            'surprise': getattr(raw_emotion, 'surprise', 0.0),
        }
        
        music_instances, is_fallback = services.get_or_create_music_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MusicResponseSerializer(music_instances, many=True)
        return Response({"mode": mode, "is_fallback": is_fallback, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary='저장된 영화 추천 조회',
    operation_description='일기 상세에 저장된 영화 추천 결과를 복원해서 반환합니다. 현재는 6차원 감정 벡터 기반 추천이 기본이며, 하위 호환용 2D(valence/arousal) 추천 로직도 서비스 계층에 함께 존재합니다.',
    responses={200: openapi.Response('조회 성공', movie_recommendation_response_schema)},
)
@swagger_auto_schema(
    method='post',
    operation_summary='감정 기반 영화 추천 생성',
    operation_description='일기의 6차원 감정 벡터를 기반으로 영화 추천 결과를 생성합니다. 요청 바디의 mode 파라미터를 통해 세 가지 추천 전략 중 하나를 사용할 수 있습니다.\n\n- maintain : 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 영화를 추천합니다 (기본값).\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 편안한 감정으로 전환(Shift)할 수 있는 영화를 추천합니다.\n- amplification: 현재의 행복하고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 흥미진진한 영화를 추천합니다.',
    request_body=serializers.ContentRecommendationRequestSerializer,
    responses={200: openapi.Response('생성 성공', movie_recommendation_response_schema)},
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_movie_view(request, diary_id):
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)

    if request.method == 'GET':
        data = services.get_saved_movie_metadata(diary_obj)
        serializer = MovieDailyRecommendedSerializer(data, many=True)
        return Response({"recommendations": serializer.data}, status=status.HTTP_200_OK)
        
    if request.method == 'POST':
        req_serializer = serializers.ContentRecommendationRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        mode = req_serializer.validated_data.get('mode', 'maintain')
        count = req_serializer.validated_data.get('count', 3)
        
        raw_emotion = getattr(diary_obj, 'emotion', None)
        user_6d_emotion = {
            'joy': getattr(raw_emotion, 'joy', 0.0),
            'sadness': getattr(raw_emotion, 'sadness', 0.0),
            'anger': getattr(raw_emotion, 'anger', 0.0),
            'fear': getattr(raw_emotion, 'fear', 0.0),
            'trust': getattr(raw_emotion, 'trust', 0.0),
            'surprise': getattr(raw_emotion, 'surprise', 0.0),
        }
        
        movie_instances, is_fallback = services.get_or_create_movie_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MovieResponseSerializer(movie_instances, many=True)
        return Response({"mode": mode,"is_fallback": is_fallback, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)