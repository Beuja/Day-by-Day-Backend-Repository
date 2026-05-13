# music_movie/views.py
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import RecommendationRequestSerializer, MusicSerializer, MovieSerializer
from . import services


@swagger_auto_schema(
    method='post',
    operation_summary="콘텐츠 추천 (음악/영화)",
    operation_description="사용자의 감정 수치를 기반으로 음악, 영화 또는 둘 다를 추천합니다.",
    security=[{'Token': []}],
    request_body=RecommendationRequestSerializer,
    responses={
        200: openapi.Response('추천 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'music': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                ),
                'movies': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                ),
                'strategy': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )),
        400: '잘못된 요청',
        401: '인증되지 않은 사용자'
    }
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_content(request):
    """감정 벡터를 기반으로 콘텐츠 추천"""
    serializer = RecommendationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    valence = serializer.validated_data['valence']
    arousal = serializer.validated_data['arousal']
    content_type = serializer.validated_data['content_type']
    mode = serializer.validated_data.get('mode', 'maintain')
    count = serializer.validated_data.get('count', 5)
    
    result = {}
    
    # 음악 추천
    if content_type in ['music', 'both']:
        music_list = services.recommend_music(valence, arousal, mode, count)
        result['music'] = MusicSerializer(music_list, many=True).data
    
    # 영화 추천
    if content_type in ['movie', 'both']:
        movie_list = services.recommend_movies(valence, arousal, mode, count)
        result['movies'] = MovieSerializer(movie_list, many=True).data
    
    result['strategy'] = mode
    result['target_emotion'] = {
        'valence': valence,
        'arousal': arousal
    }
    
    return Response(result, status=status.HTTP_200_OK)
