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
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='최종 결정 및 적용된 추천 전략 모드 (maintain, shift, amplification)'),
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
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='최종 결정 및 적용된 추천 전략 모드 (maintain, shift, amplification)'),
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
    operation_description='일기의 6차원 감정 벡터를 기반으로 음악 추천 결과를 생성합니다. 요청 바디의 mode 파라미터를 통해 추천 전략을 사용할 수 있습니다.\n\n- auto: 최근 5일간의 감정 누적 이력(평균 및 분산)을 분석하여 기분 유지(maintain), 전환(shift), 극대화(amplification) 중 가장 알맞은 전략을 백엔드에서 자율 결정합니다 (기본값).\n- maintain: 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 음악을 추천합니다.\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 밝은 감정으로 전환(Shift)할 수 있는 음악을 추천합니다.\n- amplification: 현재의 신나고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 신나는 음악을 추천합니다.',
    request_body=serializers.ContentRecommendationRequestSerializer,
    responses={200: openapi.Response('생성 성공', music_recommendation_response_schema)},
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_music_view(request, diary_id):
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)
    recommend_date = diary_obj.created_at.date().strftime("%Y-%m-%d")
    
    if request.method == 'GET':
        data = services.get_saved_music_metadata(diary_obj)
        serializer = MusicDailyRecommendedSerializer(data, many=True)
        res_data = serializer.data
        for item in res_data:
            item['diary_id'] = diary_id
            item['recommend_date'] = recommend_date
        return Response({"recommendations": res_data}, status=status.HTTP_200_OK)
        
    if request.method == 'POST':
        req_serializer = serializers.ContentRecommendationRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        mode = req_serializer.validated_data.get('mode', 'auto')
        count = req_serializer.validated_data.get('count', 3)
        
        if mode == 'auto':
            from daybydaybackend.diary.services import determine_auto_recommendation_mode
            mode = determine_auto_recommendation_mode(request.user, diary_obj)
        
        raw_emotion = getattr(diary_obj, 'emotion', None)
        user_6d_emotion = {
            'joy': getattr(raw_emotion, 'joy', 0.0),
            'sadness': getattr(raw_emotion, 'sadness', 0.0),
            'anger': getattr(raw_emotion, 'anger', 0.0),
            'fear': getattr(raw_emotion, 'fear', 0.0),
            'trust': getattr(raw_emotion, 'trust', 0.0),
            'surprise': getattr(raw_emotion, 'surprise', 0.0),
        }
        
        music_instances, is_fallback = services.get_or_create_music_recommendation(diary_obj, user_6d_emotion, mode, count, user=request.user)
        res_serializer = serializers.MusicResponseSerializer(music_instances, many=True)
        res_data = res_serializer.data
        for item in res_data:
            item['diary_id'] = diary_id
            item['recommend_date'] = recommend_date
        return Response({"mode": mode, "is_fallback": is_fallback, "recommendations": res_data}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary='저장된 영화 추천 조회',
    operation_description='일기 상세에 저장된 영화 추천 결과를 복원해서 반환합니다. 현재는 6차원 감정 벡터 기반 추천이 기본이며, 하위 호환용 2D(valence/arousal) 추천 로직도 서비스 계층에 함께 존재합니다.',
    responses={200: openapi.Response('조회 성공', movie_recommendation_response_schema)},
)
@swagger_auto_schema(
    method='post',
    operation_summary='감정 기반 영화 추천 생성',
    operation_description='일기의 6차원 감정 벡터를 기반으로 영화 추천 결과를 생성합니다. 요청 바디의 mode 파라미터를 통해 추천 전략을 사용할 수 있습니다.\n\n- auto: 최근 5일간의 감정 누적 이력(평균 및 분산)을 분석하여 기분 유지(maintain), 전환(shift), 극대화(amplification) 중 가장 알맞은 전략을 백엔드에서 자율 결정합니다 (기본값).\n- maintain: 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 영화를 추천합니다.\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 편안한 감정으로 전환(Shift)할 수 있는 영화를 추천합니다.\n- amplification: 현재의 행복하고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 흥미진진한 영화를 추천합니다.',
    request_body=serializers.ContentRecommendationRequestSerializer,
    responses={200: openapi.Response('생성 성공', movie_recommendation_response_schema)},
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_movie_view(request, diary_id):
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)
    recommend_date = diary_obj.created_at.date().strftime("%Y-%m-%d")

    if request.method == 'GET':
        data = services.get_saved_movie_metadata(diary_obj)
        serializer = MovieDailyRecommendedSerializer(data, many=True)
        res_data = serializer.data
        for item in res_data:
            item['diary_id'] = diary_id
            item['recommend_date'] = recommend_date
        return Response({"recommendations": res_data}, status=status.HTTP_200_OK)
        
    if request.method == 'POST':
        req_serializer = serializers.ContentRecommendationRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        mode = req_serializer.validated_data.get('mode', 'auto')
        count = req_serializer.validated_data.get('count', 3)
        
        if mode == 'auto':
            from daybydaybackend.diary.services import determine_auto_recommendation_mode
            mode = determine_auto_recommendation_mode(request.user, diary_obj)
        
        raw_emotion = getattr(diary_obj, 'emotion', None)
        user_6d_emotion = {
            'joy': getattr(raw_emotion, 'joy', 0.0),
            'sadness': getattr(raw_emotion, 'sadness', 0.0),
            'anger': getattr(raw_emotion, 'anger', 0.0),
            'fear': getattr(raw_emotion, 'fear', 0.0),
            'trust': getattr(raw_emotion, 'trust', 0.0),
            'surprise': getattr(raw_emotion, 'surprise', 0.0),
        }
        
        movie_instances, is_fallback = services.get_or_create_movie_recommendation(diary_obj, user_6d_emotion, mode, count, user=request.user)
        res_serializer = serializers.MovieResponseSerializer(movie_instances, many=True)
        res_data = res_serializer.data
        for item in res_data:
            item['diary_id'] = diary_id
            item['recommend_date'] = recommend_date
        return Response({"mode": mode, "is_fallback": is_fallback, "recommendations": res_data}, status=status.HTTP_200_OK)