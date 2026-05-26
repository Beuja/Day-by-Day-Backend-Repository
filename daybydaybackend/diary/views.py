from django.db import transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Diary, DailyRecommended
from .serializers import (
    DiarySerializer, AnalyzeEmotionRequestSerializer,
    DiaryCreateRequestSerializer,
    MainRecommendationResponseSerializer, CalendarResponseSerializer
)
from . import services


# Swagger에 노출할 메인 추천 응답 스키마 상세 정의
main_recommendation_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'has_diaries': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="해당 유저의 최근 일기 작성 데이터가 존재하여 추천이 가능한지 여부"),
        'is_fallback': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="도서 추천이 사용량 부족 등으로 인해 대체(Fallback) 추천되었는지 여부"),
        'emotion_status': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'joy': openapi.Schema(type=openapi.TYPE_NUMBER),
                'sadness': openapi.Schema(type=openapi.TYPE_NUMBER),
                'anger': openapi.Schema(type=openapi.TYPE_NUMBER),
                'fear': openapi.Schema(type=openapi.TYPE_NUMBER),
                'trust': openapi.Schema(type=openapi.TYPE_NUMBER),
                'surprise': openapi.Schema(type=openapi.TYPE_NUMBER),
                'valence': openapi.Schema(type=openapi.TYPE_NUMBER),
                'arousal': openapi.Schema(type=openapi.TYPE_NUMBER),
            },
            description="최근 5개 일기의 Plutchik 6대 감정 평균 수치 (일기가 전혀 없으면 null)",
            allow_null=True
        ),
        'books': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'isbn': openapi.Schema(type=openapi.TYPE_STRING, description="도서 ISBN 번호"),
                    'title': openapi.Schema(type=openapi.TYPE_STRING, description="도서 제목"),
                    'author': openapi.Schema(type=openapi.TYPE_STRING, description="저자 이름"),
                    'cover_url': openapi.Schema(type=openapi.TYPE_STRING, description="도서 표지 자켓 이미지 URL"),
                    'category': openapi.Schema(type=openapi.TYPE_STRING, description="도서 카테고리/장르"),
                    'description': openapi.Schema(type=openapi.TYPE_STRING, description="도서 소개 미리보기 텍스트"),
                }
            ),
            description="맞춤형 추천 도서 목록 2개 (일기가 전혀 없으면 빈 배열)"
        ),
        'music': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'track_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="음악 트랙 ID"),
                    'title': openapi.Schema(type=openapi.TYPE_STRING, description="음악 제목"),
                    'artist': openapi.Schema(type=openapi.TYPE_STRING, description="아티스트명"),
                    'image_url': openapi.Schema(type=openapi.TYPE_STRING, description="앨범 커버 이미지 URL"),
                    'tags': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_STRING),
                        description="음악 태그 리스트"
                    ),
                    'score': openapi.Schema(type=openapi.TYPE_NUMBER, description="추천 매칭 점수 (낮을수록 매칭도 우수)"),
                }
            ),
            description="맞춤형 추천 음악 목록 2개 (일기가 전혀 없으면 빈 배열)"
        ),
        'movies': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'movie_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="영화 ID"),
                    'title': openapi.Schema(type=openapi.TYPE_STRING, description="영화 제목"),
                    'director': openapi.Schema(type=openapi.TYPE_STRING, description="감독명"),
                    'image_url': openapi.Schema(type=openapi.TYPE_STRING, description="영화 포스터 이미지 URL"),
                    'tags': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_STRING),
                        description="영화 태그 리스트"
                    ),
                    'score': openapi.Schema(type=openapi.TYPE_NUMBER, description="추천 매칭 점수 (낮을수록 매칭도 우수)"),
                }
            ),
            description="맞춤형 추천 영화 목록 2개 (일기가 전혀 없으면 빈 배열)"
        ),
    }
)


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
    
    diary = services.create_diary_entry(
        user=request.user,
        content=serializer.validated_data['content'],
        weather=serializer.validated_data.get('weather'),
        image=serializer.validated_data.get('image')
    )

    response_serializer = DiarySerializer(diary)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


# ===== 일기 감정 분석 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="일기 감정 분석",
    operation_description="저장되어 있는 일기 ID를 받아와 감정을 분석하고 결과를 DB에 저장/업데이트 합니다.",
    security=[{'Token': []}],
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
@transaction.atomic
def analyze_diary_emotion(request):
    serializer = AnalyzeEmotionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    diary_id = serializer.validated_data['diary_id']
        
    try:
        diary = services.process_diary_emotion(diary_id=diary_id, user=request.user)
    except Diary.DoesNotExist:
        return Response({'message': '해당 일기를 찾을 수 없거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = DiarySerializer(diary)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ===== 메인 화면 통합 개인화 추천 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="메인 화면 통합 개인화 추천",
    operation_description="최근 작성한 5개 일기의 감정을 종합 분석하여 책, 음악, 영화를 분야별로 2개씩 추출해 통합 반환합니다. 작성된 일기가 없는 신규 유저 시나리오(has_diaries=False, 빈 리스트 반환)도 상세히 표시됩니다.",
    security=[{'Token': []}],
    manual_parameters=[
        openapi.Parameter('mode', openapi.IN_QUERY, description="추천 모드 (maintain, shift, amplification)", type=openapi.TYPE_STRING, required=False)
    ],
    responses={
        200: openapi.Response('추천 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mode': openapi.Schema(type=openapi.TYPE_STRING, description="적용된 추천 전략 모드"), # 💡 모드 반환 추가
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
    from daybydaybackend.books.services import recommend_books
    from daybydaybackend.music_movie.recommend_music_movie.recommend_music import MusicEmotionRecommender
    from daybydaybackend.music_movie.recommend_music_movie.recommend_movie import MovieEmotionRecommender
    from daybydaybackend.music_movie.services import load_music_data, load_movie_data
    from daybydaybackend.music_movie.serializers import MusicResponseSerializer, MovieResponseSerializer
    
    # 💡 URL 파라미터에서 mode 읽어오기 (기본값 maintain)
    current_mode = request.query_params.get('mode', 'maintain')
    if current_mode not in ['maintain', 'shift', 'amplification']:
        current_mode = 'maintain'
        
    diaries = Diary.objects.filter(user=request.user).select_related('emotion')[:5]
    emotions = [d.emotion for d in diaries if hasattr(d, 'emotion') and d.emotion is not None]
    
    if not emotions:
        return Response({
            'mode': current_mode,
            'emotion_status': {
                'joy': 0.0, 'sadness': 0.0, 'anger': 0.0, 'fear': 0.0, 'trust': 0.0, 'surprise': 0.0,
                'valence': 0.0, 'arousal': 0.0
            },
            'books': [], 'music': [], 'movies': []
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
        
    user_6d_emotion = {k: avg_emotion[k] for k in ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']}
    
    # 💡 하드코딩되었던 maintain을 동적 변수 current_mode 로 교체
    books = recommend_books(user_6d_emotion, mode=current_mode, count=2)
    
    music_recommender = MusicEmotionRecommender()
    movie_recommender = MovieEmotionRecommender()
    music_result = music_recommender.recommend_music(user_6d_emotion, load_music_data(), mode=current_mode, top_n=2)
    movie_result = movie_recommender.recommend_movies(user_6d_emotion, load_movie_data(), mode=current_mode, top_n=2)
    
    music_list = music_result.get('recommendations', [])
    movie_list = movie_result.get('recommendations', [])
    
    serialized_books = []
    for b in books:
        serialized_books.append({
            'isbn': b.isbn,
            'title': b.title,
            'author': b.author,
            'category': b.category,
            'description': b.description[:100] + '...' if b.description and len(b.description) > 100 else (b.description or ""),
            'valence': b.valence,
            'arousal': b.arousal,
        })
        
    serialized_music = MusicResponseSerializer(music_list, many=True).data
    serialized_movies = MovieResponseSerializer(movie_list, many=True).data

    # 💡 분석 결과 DB 캐싱 및 모드(mode) 기록
    if diaries.exists():
        latest_diary = diaries[0]
        daily_rec, created = DailyRecommended.objects.get_or_create(diary=latest_diary)
        
        daily_rec.mode = current_mode # 모드 저장
        
        book_pks = [b.pk for b in books]
        music_pks = [m.id if hasattr(m, 'id') else m.get('track_id') for m in music_list if m]
        movie_pks = [m.tmdb_id if hasattr(m, 'tmdb_id') else m.get('movie_id') for m in movie_list if m]

        daily_rec.books.set(book_pks)
        daily_rec.music.set(music_pks)
        daily_rec.movies.set(movie_pks)
        daily_rec.save()

    return Response({
        'mode': current_mode, # 💡 최종 응답 상단에 모드 출력
        'emotion_status': avg_emotion,
        'books': serialized_books,
        'music': serialized_music,
        'movies': serialized_movies
    }, status=status.HTTP_200_OK)