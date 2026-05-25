from django.db import transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser


from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Diary
from .serializers import (
    DiarySerializer, AnalyzeEmotionRequestSerializer,
    DiaryCreateRequestSerializer,
    BookSerializer, MovieSerializer, MusicSerializer
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
@parser_classes([MultiPartParser, FormParser])
def create_diary(request):
    serializer = DiaryCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # 생성 로직은 services 로 분리
    diary = services.create_diary_entry(
        user=request.user,
        content=serializer.validated_data['content'],
        weather=serializer.validated_data.get('weather'),
        image=serializer.validated_data.get('image')
    )

    
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
@parser_classes([JSONParser, MultiPartParser, FormParser])
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


# ===== 메인 화면 통합 개인화 추천 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="메인 화면 통합 개인화 추천",
    operation_description="최근 작성한 5개 일기의 감정을 종합 분석하여 책, 음악, 영화를 분야별로 2개씩 추출해 통합 반환합니다.",
    security=[{'Token': []}],
    responses={
        200: openapi.Response('추천 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'emotion_status': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='사용자의 분석된 평균 감정 상태'
                ),
                'books': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                'music': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                'movies': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
            }
        )),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_main_recommendations(request):
    """
    최근 일기 5개의 감정을 분석하여 분야별 2개 콘텐츠 통합 맞춤 추천 반환.
    작성된 일기가 없는 경우 Option A (has_diaries=False, 빈 리스트 반환) 방식을 취합니다.
    """
    from daybydaybackend.books.services import recommend_books
    from daybydaybackend.music_movie.recommend_music_movie.recommend_music import MusicEmotionRecommender
    from daybydaybackend.music_movie.recommend_music_movie.recommend_movie import MovieEmotionRecommender
    from daybydaybackend.music_movie.services import load_music_data, load_movie_data
    
    # 1. 최근 5개 일기 및 감정정보 조회 (select_related 적용으로 N+1 문제 해소)
    diaries = Diary.objects.filter(user=request.user).select_related('emotion')[:5]
    
    # 2. 작성된 일기가 아예 없거나 감정 분석 데이터가 하나도 없는 신규 유저 예외 처리 (Option A)
    emotions = [d.emotion for d in diaries if hasattr(d, 'emotion') and d.emotion is not None]
    
    if not emotions:
        return Response({
            'has_diaries': False,
            'emotion_status': None,
            'books': [],
            'music': [],
            'movies': []
        }, status=status.HTTP_200_OK)
        
    count = len(emotions)
    avg_emotion = {
        'joy': round(sum(e.joy for e in emotions) / count, 4),
        'sadness': round(sum(e.sadness for e in emotions) / count, 4),
        'anger': round(sum(e.anger for e in emotions) / count, 4),
        'fear': round(sum(e.fear for e in emotions) / count, 4),
        'trust': round(sum(e.trust for e in emotions) / count, 4),
        'surprise': round(sum(e.surprise for e in emotions) / count, 4),
        'valence': round(sum(e.valence for e in emotions) / count, 4),
        'arousal': round(sum(e.arousal for e in emotions) / count, 4),
    }
        
    # 3. 6차원 감정 기반 음악 및 영화와 보조를 맞춰 책 추천 6D 호출
    user_6d_emotion = {
        'joy': avg_emotion['joy'],
        'sadness': avg_emotion['sadness'],
        'anger': avg_emotion['anger'],
        'fear': avg_emotion['fear'],
        'trust': avg_emotion['trust'],
        'surprise': avg_emotion['surprise'],
    }
    
    books = recommend_books(user_6d_emotion, mode='maintain', count=2)
    
    # 4. 6차원 음악 및 영화 추천 API 호출
    music_recommender = MusicEmotionRecommender()
    movie_recommender = MovieEmotionRecommender()
    music_result = music_recommender.recommend_music(user_6d_emotion, load_music_data(), mode='maintain', top_n=2)
    movie_result = movie_recommender.recommend_movies(user_6d_emotion, load_movie_data(), mode='maintain', top_n=2)
    
    # 5. 데이터 정제 및 직렬화
    serialized_books = BookSerializer(books, many=True).data
    serialized_music = MusicSerializer(music_result.get('recommendations', []), many=True).data
    serialized_movies = MovieSerializer(movie_result.get('recommendations', []), many=True).data

    # 6. DailyRecommended 캐시에 추천 콘텐츠 저장 (가장 최신의 일기 객체를 기준점으로 복원 캐싱)
    if diaries.exists():
        from .models import DailyRecommended
        latest_diary = diaries[0]
        daily_rec, created = DailyRecommended.objects.get_or_create(diary=latest_diary)
        
        book_pks = [book.pk for book in books]
        music_pks = [music.pk for music in music_result.get('recommendations', [])]
        movie_pks = [movie.pk for movie in movie_result.get('recommendations', [])]

        daily_rec.books.set(book_pks)
        daily_rec.music.set(music_pks)
        daily_rec.movies.set(movie_pks)

    return Response({
        'has_diaries': True,
        'emotion_status': avg_emotion,
        'books': serialized_books,
        'music': serialized_music,
        'movies': serialized_movies
    }, status=status.HTTP_200_OK)
