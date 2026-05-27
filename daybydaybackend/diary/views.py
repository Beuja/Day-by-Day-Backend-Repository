from django.db import transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Diary, DailyRecommended, UserFeedback
from .serializers import (
    DiarySerializer, AnalyzeEmotionRequestSerializer,
    DiaryCreateRequestSerializer,
    MainRecommendationResponseSerializer, CalendarResponseSerializer,
    UserFeedbackRequestSerializer, UserPreferenceProfileResponseSerializer
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


# Swagger에 노출할 메인 추천 응답 스키마 상세 정의
main_recommendation_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'has_diaries': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="해당 유저의 최근 일기 작성 데이터가 존재하여 추천이 가능한지 여부"),
        'is_fallback': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="도서 추천이 사용량 부족 등으로 인해 대체(Fallback) 추천되었는지 여부"),
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description="적용된 추천 전략 모드 (maintain, shift, amplification)"),
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
        200: openapi.Response('추천 성공 (감정 분석 결과 및 추천 목록)', main_recommendation_response_schema),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_main_recommendations(request):
    from daybydaybackend.books.services import get_or_create_book_recommendation
    from daybydaybackend.music_movie.services import get_or_create_music_recommendation, get_or_create_movie_recommendation
    from daybydaybackend.diary.services import get_user_recent_average_emotion
    from daybydaybackend.music_movie.serializers import MusicResponseSerializer, MovieResponseSerializer
    
    current_mode = request.query_params.get('mode', 'maintain')
    if current_mode not in ['maintain', 'shift', 'amplification']:
        current_mode = 'maintain'
        
    avg_emotion, diaries = get_user_recent_average_emotion(request.user)
    
    if not avg_emotion:
        return Response({
            'has_diaries': False,
            'is_fallback': False,
            'mode': current_mode,
            'emotion_status': None,
            'books': [],
            'music': [],
            'movies': []
        }, status=status.HTTP_200_OK)
        
    latest_diary = diaries[0]
    user_6d_emotion = {k: avg_emotion[k] for k in ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']}
    
    books, is_fallback = get_or_create_book_recommendation(latest_diary, user_6d_emotion, current_mode, count=2, user=request.user)
    music_list, is_fallback_music = get_or_create_music_recommendation(latest_diary, user_6d_emotion, current_mode, count=2, user=request.user)
    movie_list, is_fallback_movie = get_or_create_movie_recommendation(latest_diary, user_6d_emotion, current_mode, count=2, user=request.user)
    
    serialized_books = []
    for b in books:
        serialized_books.append({
            'isbn': getattr(b, 'isbn', ''),
            'title': getattr(b, 'title', ''),
            'author': getattr(b, 'author', ''),
            'category': getattr(b, 'category', ''),
            'description': getattr(b, 'description', '')[:100] + '...' if getattr(b, 'description', '') and len(getattr(b, 'description', '')) > 100 else (getattr(b, 'description', '') or ""),
            'valence': getattr(b, 'valence', 0.0),
            'arousal': getattr(b, 'arousal', 0.0),
        })
        
    serialized_music = MusicResponseSerializer(music_list, many=True).data
    serialized_movies = MovieResponseSerializer(movie_list, many=True).data

    return Response({
        'has_diaries': True,
        'is_fallback': is_fallback,
        'mode': current_mode,
        'emotion_status': avg_emotion,
        'books': serialized_books,
        'music': serialized_music,
        'movies': serialized_movies
    }, status=status.HTTP_200_OK)



# ===== 월별 캘린더 감정 조회 API (복구됨!) =====
@swagger_auto_schema(
    method='get',
    operation_summary="월별 캘린더 감정 조회 (해시맵 방식)",
    operation_description="연도(year)와 월(month)을 입력받아 해당 월의 일기 작성 데이터 및 감정 요약본을 날짜별(YYYY-MM-DD) 해시맵 구조로 반환합니다.",
    security=[{'Token': []}],
    manual_parameters=[
        openapi.Parameter('year', openapi.IN_QUERY, description="조회할 연도", type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter('month', openapi.IN_QUERY, description="조회할 월", type=openapi.TYPE_INTEGER, required=False),
    ]
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_calendar_view(request):
    import calendar
    import re
    from datetime import date
    
    today = date.today()
    try:
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        return Response({'message': '유효하지 않은 연도 또는 월 형식입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    diaries = Diary.objects.filter(
        user=request.user,
        created_at__date__range=(start_date, end_date)
    ).select_related('emotion')
    
    calendar_data = {}
    for diary in diaries:
        date_str = diary.created_at.date().strftime("%Y-%m-%d")
        emotion = getattr(diary, 'emotion', None)
        
        emotion_key = "neutral"
        primary_emotion = "알수없음"
        
        if emotion:
            primary_emotion = emotion.primary_emotion
            emotion_values = {
                'joy': getattr(emotion, 'joy', 0.0),
                'sadness': getattr(emotion, 'sadness', 0.0),
                'anger': getattr(emotion, 'anger', 0.0),
                'fear': getattr(emotion, 'fear', 0.0),
                'trust': getattr(emotion, 'trust', 0.0),
                'surprise': getattr(emotion, 'surprise', 0.0),
            }
            if any(val > 0.0 for val in emotion_values.values()):
                emotion_key = max(emotion_values, key=emotion_values.get)
                
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


# ===== 콘텐츠 선호도 피드백 등록/수정 API =====
@swagger_auto_schema(
    method='post',
    operation_summary="콘텐츠 선호도 피드백 등록/수정",
    operation_description="추천받은 책, 음악, 영화에 대해 좋아요(True) 또는 싫어요(False) 피드백을 기록합니다. 이미 피드백이 존재하는 경우 단순 덮어쓰기 방식으로 최신 의견으로 갱신됩니다.",
    security=[{'Token': []}],
    request_body=UserFeedbackRequestSerializer,
    responses={
        200: '피드백 등록/갱신 성공',
        400: '유효하지 않은 요청 데이터',
        404: '피드백 대상 콘텐츠를 찾을 수 없음'
    }
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def register_feedback(request):
    serializer = UserFeedbackRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    ctype = serializer.validated_data['content_type']
    cid = serializer.validated_data['content_id']
    is_like = serializer.validated_data['is_like']
    
    from daybydaybackend.books.models import Book
    from daybydaybackend.music_movie.models import Music, Movie
    
    try:
        if ctype == 'book':
            book_obj = Book.objects.get(isbn=cid)
            defaults = {'is_like': is_like}
            UserFeedback.objects.update_or_create(user=request.user, book=book_obj, defaults=defaults)
        elif ctype == 'music':
            music_obj = Music.objects.get(id=int(cid))
            defaults = {'is_like': is_like}
            UserFeedback.objects.update_or_create(user=request.user, music=music_obj, defaults=defaults)
        elif ctype == 'movie':
            movie_obj = Movie.objects.get(tmdb_id=int(cid))
            defaults = {'is_like': is_like}
            UserFeedback.objects.update_or_create(user=request.user, movie=movie_obj, defaults=defaults)
    except (Book.DoesNotExist, Music.DoesNotExist, Movie.DoesNotExist, ValueError):
         return Response({'message': '피드백 대상 콘텐츠가 DB에 존재하지 않거나 식별자가 부정확합니다.'}, status=status.HTTP_404_NOT_FOUND)
         
    return Response({'message': f'{ctype} 콘텐츠에 대한 피드백이 성공적으로 갱신되었습니다.'}, status=status.HTTP_200_OK)


# ===== 유저 개인화 취향 프로필 및 통계 조회 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="유저 개인화 취향 프로필 및 통계 조회",
    operation_description="누적 좋아요/싫어요 개수와 감정 선호 프로필(평균 감정 벡터), 그리고 현재 추천에 적용 중인 개인화 반영 비율(Beta) 단계를 리턴합니다.",
    security=[{'Token': []}],
    responses={
        200: openapi.Response('조회 성공', UserPreferenceProfileResponseSerializer),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_preference_profile(request):
    feedbacks = UserFeedback.objects.filter(user=request.user)
    likes = feedbacks.filter(is_like=True)
    likes_count = likes.count()
    dislikes_count = feedbacks.filter(is_like=False).count()
    
    if likes_count == 0:
        beta = 0.0
        level = "Cold Start (일기 정서 반영 100% - 피드백 누적 필요)"
    elif likes_count <= 4:
        beta = 0.15
        level = "취향 분석 시작 (일기 정서 85% + 누적 선호 15% 반영)"
    elif likes_count <= 9:
        beta = 0.30
        level = "취향 심층 연동 (일기 정서 70% + 누적 선호 30% 반영)"
    else:
        beta = 0.40
        level = "완전 개인화 연동 (일기 정서 60% + 누적 선호 40% 반영 - 취향 고정)"
        
    avg_vector = None
    if likes_count > 0:
        joy_sum = sadness_sum = anger_sum = fear_sum = trust_sum = surprise_sum = 0.0
        vector_count = 0
        
        for fb in likes:
            item = fb.book or fb.music or fb.movie
            if item:
                joy_sum += getattr(item, 'joy', 0.0) or 0.0
                sadness_sum += getattr(item, 'sadness', 0.0) or 0.0
                anger_sum += getattr(item, 'anger', 0.0) or 0.0
                fear_sum += getattr(item, 'fear', 0.0) or 0.0
                trust_sum += getattr(item, 'trust', 0.0) or 0.0
                surprise_sum += getattr(item, 'surprise', 0.0) or 0.0
                vector_count += 1
                
        if vector_count > 0:
            avg_vector = {
                'joy': round(joy_sum / vector_count, 4),
                'sadness': round(sadness_sum / vector_count, 4),
                'anger': round(anger_sum / vector_count, 4),
                'fear': round(fear_sum / vector_count, 4),
                'trust': round(trust_sum / vector_count, 4),
                'surprise': round(surprise_sum / vector_count, 4),
            }
            
    return Response({
        'likes_count': likes_count,
        'dislikes_count': dislikes_count,
        'personalization_beta': beta,
        'personalization_level': level,
        'preferred_emotions': avg_vector
    }, status=status.HTTP_200_OK)