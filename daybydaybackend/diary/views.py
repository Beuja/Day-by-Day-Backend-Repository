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
        
    serialized_music = music_result.get('recommendations', [])
    serialized_movies = movie_result.get('recommendations', [])
    
    return Response({
        'has_diaries': True,
        'emotion_status': avg_emotion,
        'books': serialized_books,
        'music': serialized_music,
        'movies': serialized_movies
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary="월별 캘린더 감정 조회 (해시맵 방식)",
    operation_description="연도(year)와 월(month)을 입력받아 해당 월의 일기 작성 데이터 및 감정 요약본을 날짜별(YYYY-MM-DD) 해시맵 구조로 반환합니다. 작성된 일기가 없는 날짜는 키에서 누락되며, 일기가 아예 없는 월은 has_diaries=False가 내려갑니다.",
    security=[{'Token': []}],
    manual_parameters=[
        openapi.Parameter('year', openapi.IN_QUERY, description="조회할 연도 (예: 2026)", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('month', openapi.IN_QUERY, description="조회할 월 (예: 5)", type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={
        200: openapi.Response('조회 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'has_diaries': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="해당 월에 작성된 일기 존재 여부"),
                'year': openapi.Schema(type=openapi.TYPE_INTEGER),
                'month': openapi.Schema(type=openapi.TYPE_INTEGER),
                'calendar_data': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="날짜를 Key로 하는 캘린더 감정 해시맵",
                    additional_properties=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'diary_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'weather': openapi.Schema(type=openapi.TYPE_STRING),
                            'primary_emotion': openapi.Schema(type=openapi.TYPE_STRING, description="대표 감정 한글명"),
                            'emotion_key': openapi.Schema(type=openapi.TYPE_STRING, description="대표 감정 영문 식별자"),
                            'preview': openapi.Schema(type=openapi.TYPE_STRING, description="20자 내외 내용 미리보기"),
                        }
                    )
                )
            }
        )),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_calendar_view(request):
    import calendar
    import re
    from datetime import date
    
    # 1. 쿼리 파라미터 파싱 및 기본값(오늘 기준) 세팅
    today = date.today()
    try:
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'message': '유효하지 않은 연도 또는 월 형식입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
    # 2. 해당 월의 시작일과 마지막일 범위 산출
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    # 3. 로그인된 유저의 일기 중 범위 내에 포함되는 데이터 로드 (select_related로 N+1 방지)
    diaries = Diary.objects.filter(
        user=request.user,
        created_at__date__range=(start_date, end_date)
    ).select_related('emotion')
    
    # 4. 해시맵 조립
    calendar_data = {}
    for diary in diaries:
        date_str = diary.created_at.date().strftime("%Y-%m-%d")
        emotion = getattr(diary, 'emotion', None)
        
        # 기본 감정 정보 세팅
        emotion_key = "neutral"
        primary_emotion = "알수없음"
        
        if emotion:
            primary_emotion = emotion.primary_emotion
            
            # Plutchik 6대 기본 감정 수치 대조
            emotion_values = {
                'joy': getattr(emotion, 'joy', 0.0),
                'sadness': getattr(emotion, 'sadness', 0.0),
                'anger': getattr(emotion, 'anger', 0.0),
                'fear': getattr(emotion, 'fear', 0.0),
                'trust': getattr(emotion, 'trust', 0.0),
                'surprise': getattr(emotion, 'surprise', 0.0),
            }
            # 감정 중 최대값을 지닌 감정의 영문 식별자(emotion_key)를 도출
            if any(val > 0.0 for val in emotion_values.values()):
                emotion_key = max(emotion_values, key=emotion_values.get)
                
        # 본문 미리보기 정제 (20글자 내외)
        clean_content = re.sub(r'\s+', ' ', diary.content).strip()
        preview = clean_content[:20] + '...' if len(clean_content) > 20 else clean_content
        
        calendar_data[date_str] = {
            "diary_id": diary.id,
            "weather": diary.weather,
            "primary_emotion": primary_emotion,
            "emotion_key": emotion_key,
            "preview": preview
        }
        
    return Response({
        "has_diaries": bool(calendar_data),
        "year": year,
        "month": month,
        "calendar_data": calendar_data
    }, status=status.HTTP_200_OK)
