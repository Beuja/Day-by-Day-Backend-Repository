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


diary_id_path_parameter = openapi.Parameter(
    name='diary_id',
    in_=openapi.IN_PATH,
    description='추천 대상 일기 ID',
    type=openapi.TYPE_INTEGER,
    required=True,
)

music_properties = {
    'track_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="음악 트랙 ID"),
    'title': openapi.Schema(type=openapi.TYPE_STRING, description="음악 제목"),
    'artist': openapi.Schema(type=openapi.TYPE_STRING, description="아티스트명"),
    'image_url': openapi.Schema(type=openapi.TYPE_STRING, description="앨범 커버 이미지 URL"),
    'tags': openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=openapi.Schema(type=openapi.TYPE_STRING),
        description="음악 태그 리스트"
    ),
    'score': openapi.Schema(type=openapi.TYPE_NUMBER, description="감정 가중치 및 대중성 반영 추천 매칭 점수 (낮을수록 감정과 가깝거나 매칭도가 높은 순위)"),
}

movie_properties = {
    'movie_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="영화 ID"),
    'title': openapi.Schema(type=openapi.TYPE_STRING, description="영화 제목"),
    'director': openapi.Schema(type=openapi.TYPE_STRING, description="감독명"),
    'image_url': openapi.Schema(type=openapi.TYPE_STRING, description="영화 포스터 이미지 URL"),
    'tags': openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=openapi.Schema(type=openapi.TYPE_STRING),
        description="영화 태그 리스트"
    ),
    'score': openapi.Schema(type=openapi.TYPE_NUMBER, description="감정 가중치 및 대중성 반영 추천 매칭 점수 (낮을수록 감정과 가깝거나 매칭도가 높은 순위)"),
}

music_get_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'recommendations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT, properties=music_properties),
            description='일기 상세에 저장 및 복원된 음악 추천 목록',
        ),
    },
)

music_post_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 음악 추천 전략 모드 (maintain, shift, amplification)'),
        'recommendations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT, properties=music_properties),
            description='감정 기반으로 실시간 맞춤 생성된 추천 음악 목록',
        ),
    },
)

movie_get_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'recommendations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT, properties=movie_properties),
            description='일기 상세에 저장 및 복원된 영화 추천 목록',
        ),
    },
)

movie_post_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='적용된 영화 추천 전략 모드 (maintain, shift, amplification)'),
        'recommendations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT, properties=movie_properties),
            description='감정 기반으로 실시간 맞춤 생성된 추천 영화 목록',
        ),
    },
)


@swagger_auto_schema(
    method='get',
    operation_summary='저장된 음악 추천 조회',
    operation_description='일기 상세에 저장된 음악 추천 결과를 복원해서 반환합니다. 현재는 6차원 감정 벡터 기반 추천이 기본이며, 하위 호환용 2D(valence/arousal) 추천 로직도 서비스 계층에 함께 존재합니다.',
    manual_parameters=[diary_id_path_parameter],
    responses={200: openapi.Response('조회 성공', music_get_response_schema)},
)
@swagger_auto_schema(
    method='post',
    operation_summary='감정 기반 음악 추천 생성',
    operation_description='일기의 6차원 감정 벡터를 기반으로 음악 추천 결과를 생성합니다. 요청 바디의 mode 파라미터를 통해 세 가지 추천 전략 중 하나를 사용할 수 있습니다.\n\n- maintain: 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 음악을 추천합니다 (기본값).\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 밝은 감정으로 전환(Shift)할 수 있는 음악을 추천합니다.\n- amplification: 현재의 신나고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 신나는 음악을 추천합니다.',
    request_body=serializers.ContentRecommendationRequestSerializer,
    responses={200: openapi.Response('생성 성공', music_post_response_schema)},
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_music_view(request, diary_id):
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)
    
    if request.method == 'GET':
        data = services.get_saved_music_metadata(diary_obj)
        serializer = serializers.MusicResponseSerializer(data, many=True)
        
        # DB에서 저장된 모드를 직접 읽어와 반환합니다
        mode = "maintain"
        try:
            daily_rec = DailyRecommended.objects.get(diary=diary_obj)
            mode = getattr(daily_rec, 'mode', 'maintain')
        except DailyRecommended.DoesNotExist:
            pass
            
        return Response({"mode": mode, "recommendations": serializer.data}, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
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
        
        data = services.get_or_create_music_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MusicResponseSerializer(data, many=True)
        return Response({"mode": mode, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary='저장된 영화 추천 조회',
    operation_description='일기 상세에 저장된 영화 추천 결과를 복원해서 반환합니다. 현재는 6차원 감정 벡터 기반 추천이 기본이며, 하위 호환용 2D(valence/arousal) 추천 로직도 서비스 계층에 함께 존재합니다.',
    manual_parameters=[diary_id_path_parameter],
    responses={200: openapi.Response('조회 성공', movie_get_response_schema)},
)
@swagger_auto_schema(
    method='post',
    operation_summary='감정 기반 영화 추천 생성',
    operation_description='일기의 6차원 감정 벡터를 기반으로 영화 추천 결과를 생성합니다. 요청 바디의 mode 파라미터를 통해 세 가지 추천 전략 중 하나를 사용할 수 있습니다.\n\n- maintain : 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 영화를 추천합니다 (기본값).\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 편안한 감정으로 전환(Shift)할 수 있는 영화를 추천합니다.\n- amplification: 현재의 행복하고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 흥미진진한 영화를 추천합니다.',
    request_body=serializers.ContentRecommendationRequestSerializer,
    responses={200: openapi.Response('생성 성공', movie_post_response_schema)},
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_movie_view(request, diary_id):
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)
    
    if request.method == 'GET':
        data = services.get_saved_movie_metadata(diary_obj)
        serializer = serializers.MovieResponseSerializer(data, many=True)
        
        # DB에서 저장된 모드를 직접 읽어와 반환합니다
        mode = "maintain"
        try:
            daily_rec = DailyRecommended.objects.get(diary=diary_obj)
            mode = getattr(daily_rec, 'mode', 'maintain')
        except DailyRecommended.DoesNotExist:
            pass
            
        return Response({"mode": mode, "recommendations": serializer.data}, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
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
        
        data = services.get_or_create_movie_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MovieResponseSerializer(data, many=True)
        return Response({"mode": mode, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)