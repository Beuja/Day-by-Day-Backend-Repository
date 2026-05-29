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
    MainRecommendationResponseSerializer, CalendarResponseSerializer,
    DiaryEmpathyResponseSerializer
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
    from django.utils import timezone
    import datetime
    
    # USE_TZ=False 환경에서는 timezone.now()가 이미 naive local datetime입니다.
    now_local = timezone.now()
    today_date = now_local.date()
    
    # naive datetime 시작/끝 시간대 설정 (SQLite USE_TZ=False 완벽 대응)
    today_start = datetime.datetime.combine(today_date, datetime.time.min)
    today_end = datetime.datetime.combine(today_date, datetime.time.max)
    
    # 오늘 이미 작성된 일기가 있는지 확인
    existing_diary = Diary.objects.filter(
        user=request.user,
        created_at__range=(today_start, today_end)
    ).exists()
    
    if existing_diary:
        return Response({
            "is_diary": False,
            "message": "오늘은 이미 일기를 작성하셨습니다."
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = DiaryCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    diary = services.create_diary_entry(
        user=request.user,
        content=serializer.validated_data['content'],
        weather=serializer.validated_data.get('weather'),
        image=serializer.validated_data.get('image')
    )

    response_serializer = DiarySerializer(diary)
    data = response_serializer.data
    data['is_diary'] = True
    return Response(data, status=status.HTTP_201_CREATED)


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
        'musics': openapi.Schema(
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
    from daybydaybackend.books.services import recommend_books
    from daybydaybackend.music_movie.recommend_music_movie.recommend_music import MusicEmotionRecommender
    from daybydaybackend.music_movie.recommend_music_movie.recommend_movie import MovieEmotionRecommender
    from daybydaybackend.music_movie.services import load_music_data, load_movie_data
    from daybydaybackend.music_movie.serializers import MusicResponseSerializer, MovieResponseSerializer
    
    current_mode = request.query_params.get('mode', 'maintain')
    if current_mode not in ['maintain', 'shift', 'amplification']:
        current_mode = 'maintain'
        
    diaries = Diary.objects.filter(user=request.user).select_related('emotion')[:5]
    emotions = [d.emotion for d in diaries if hasattr(d, 'emotion') and d.emotion is not None]
    
    if not emotions:
        from daybydaybackend.books.models import Book
        from daybydaybackend.music_movie.serializers import MusicResponseSerializer, MovieResponseSerializer
        import random
        
        # 1. 도서 랜덤 2개 추출 및 직렬화
        random_books = []
        all_books = list(Book.objects.all()[:100])
        if all_books:
            random_books = random.sample(all_books, min(len(all_books), 2))
            
        serialized_books = []
        for b in random_books:
            serialized_books.append({
                'isbn': getattr(b, 'isbn', ''),
                'title': getattr(b, 'title', ''),
                'author': getattr(b, 'author', ''),
                'category': getattr(b, 'category', ''),
                'description': getattr(b, 'description', '')[:100] + '...' if getattr(b, 'description', '') and len(getattr(b, 'description', '')) > 100 else (getattr(b, 'description', '') or ""),
                'valence': getattr(b, 'valence', 0.0),
                'arousal': getattr(b, 'arousal', 0.0),
                'diary_id': None,
                'recommend_date': None,
            })
            
        # 2. 음악 랜덤 2개 추출 및 직렬화
        random_musics = []
        all_music_data = load_music_data()
        if all_music_data:
            random_musics = random.sample(all_music_data, min(len(all_music_data), 2))
            
        serialized_musics = MusicResponseSerializer(random_musics, many=True).data
        for item in serialized_musics:
            item['diary_id'] = None
            item['recommend_date'] = None
            
        # 3. 영화 랜덤 2개 추출 및 직렬화
        random_movies = []
        all_movie_data = load_movie_data()
        if all_movie_data:
            random_movies = random.sample(all_movie_data, min(len(all_movie_data), 2))
            
        serialized_movies = MovieResponseSerializer(random_movies, many=True).data
        for item in serialized_movies:
            item['diary_id'] = None
            item['recommend_date'] = None
            
        return Response({
            'has_diaries': False,
            'is_fallback_book': True,
            'is_fallback_movie': True,
            'is_fallback_music': True,
            'mode': current_mode,
            'emotion_status': None,
            'books': serialized_books,
            'musics': serialized_musics,
            'movies': serialized_movies
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
    
    books, is_fallback_book = recommend_books(user_6d_emotion, mode=current_mode, count=2)
    
    music_recommender = MusicEmotionRecommender()
    movie_recommender = MovieEmotionRecommender()
    music_result = music_recommender.recommend_musics(user_6d_emotion, load_music_data(), mode=current_mode, top_n=2)
    movie_result = movie_recommender.recommend_movies(user_6d_emotion, load_movie_data(), mode=current_mode, top_n=2)
    
    music_list = music_result.get('recommendations', [])
    is_fallback_music = music_result.get('is_fallback', False)
    movie_list = movie_result.get('recommendations', [])
    is_fallback_movie = movie_result.get('is_fallback', False)
    
    latest_diary = diaries[0]
    diary_id = latest_diary.id
    recommend_date = latest_diary.created_at.date().strftime("%Y-%m-%d")

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
            'diary_id': diary_id,
            'recommend_date': recommend_date,
        })
        
    serialized_musics = MusicResponseSerializer(music_list, many=True).data
    for item in serialized_musics:
        item['diary_id'] = diary_id
        item['recommend_date'] = recommend_date

    serialized_movies = MovieResponseSerializer(movie_list, many=True).data
    for item in serialized_movies:
        item['diary_id'] = diary_id
        item['recommend_date'] = recommend_date

    if diaries.exists():
        latest_diary = diaries[0]
        daily_rec, created = DailyRecommended.objects.get_or_create(
            diary=latest_diary,
            mode=current_mode
        )
        
        book_pks = [b.pk for b in books]
        music_pks = [m.id if hasattr(m, 'id') else m.get('track_id') for m in music_list if m]
        movie_pks = [m.tmdb_id if hasattr(m, 'tmdb_id') else m.get('movie_id') for m in movie_list if m]

        daily_rec.books.set(book_pks)
        daily_rec.musics.set(music_pks)
        daily_rec.movies.set(movie_pks)
        daily_rec.save()

    return Response({
        'has_diaries': True,
        'is_fallback_book': is_fallback_book,
        'is_fallback_movie': is_fallback_movie,
        'is_fallback_music': is_fallback_music,
        'mode': current_mode,
        'emotion_status': avg_emotion,
        'books': serialized_books,
        'musics': serialized_musics,
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


# ===== 최근 일기 기반 실시간 공감 멘트 조회 API (Plan C) =====
@swagger_auto_schema(
    method='get',
    operation_summary="최근 일기 기반 실시간 공감 멘트 조회",
    operation_description="최근 작성한 최대 5개의 일기 감정을 종합 분석하여 가장 지배적인 대표 감정을 파악하고, 그에 맞는 따뜻하고 다정한 공감 문장과 콘텐츠 추천 유도 멘트를 결합하여 반환합니다. 작성된 일기가 없는 신규 유저에게는 격려와 기본 웰컴 안전 문구를 반환합니다.",
    security=[{'Token': []}],
    responses={
        200: openapi.Response('공감 멘트 반환 성공', DiaryEmpathyResponseSerializer),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_diary_empathy_message(request):
    import random
    
    # 최근 5개의 일기를 최신순으로 가져옴
    diaries = Diary.objects.filter(user=request.user).select_related('emotion')[:5]
    emotions = [d.emotion for d in diaries if hasattr(d, 'emotion') and d.emotion is not None]
    
    # 일기가 없는 경우
    if not emotions:
        return Response({
            'has_diaries': False,
            'primary_emotion': None,
            'empathy_message': "오늘의 첫 일기를 작성하고 DDB의 따뜻한 공감을 받아보세요! 🔮"
        }, status=status.HTTP_200_OK)
        
    count = len(emotions)
    avg_emotion = {
        'joy': sum(e.joy for e in emotions) / count,
        'sadness': sum(e.sadness for e in emotions) / count,
        'anger': sum(e.anger for e in emotions) / count,
        'fear': sum(e.fear for e in emotions) / count,
        'trust': sum(e.trust for e in emotions) / count,
        'surprise': sum(e.surprise for e in emotions) / count,
    }
    
    label_map = {
        'joy': '기쁨',
        'sadness': '슬픔',
        'anger': '분노',
        'fear': '두려움',
        'trust': '신뢰',
        'surprise': '놀람',
    }
    
    # 평균값이 가장 높은 감정 찾기
    primary_key = max(label_map.keys(), key=lambda k: avg_emotion.get(k, 0.0))
    
    # 감정의 평균값이 0 이하(모두 0인 경우 등)이면 알수없음 처리
    if avg_emotion.get(primary_key, 0.0) <= 0:
        primary_emotion = '알수없음'
    else:
        primary_emotion = label_map[primary_key]
        
    # 감정별 5종 공감 멘트 템플릿 라이브러리
    empathy_templates = {
        '기쁨': [
            "오늘 하루는 눈부신 햇살처럼 가득 차오르는 기쁨이 함께했군요. 당신의 환한 미소가 여기까지 전해되는 듯해 제 마음도 덩달아 설렙니다.",
            "마음 깊이 행복이 스며든 오늘, 당신의 소중하고 기쁜 순간을 함께 나눌 수 있어 정말 감사한 하루예요.",
            "벅차오르는 기쁨과 긍정의 에너지가 일기장에 가득 묻어나네요. 이 빛나는 순간이 오래오래 당신의 곁에 머물기를 소망합니다.",
            "스스로를 미소 짓게 만드는 멋진 일들이 있었네요! 당신의 오늘이 그 어떤 날보다 반짝이고 따뜻해서 참 다행입니다.",
            "기분 좋은 멜로디가 귓가에 맴도는 듯한 행복한 하루였군요. 이 따스한 정취를 온전히 마음에 담아두고 싶어집니다."
        ],
        '슬픔': [
            "많이 버겁고 가슴이 시린 하루를 보내셨군요. 무거운 슬픔을 혼자 짊어지느라 애쓰셨을 당신을 따뜻하게 안아드리고 싶어요.",
            "이유 모를 공허함이나 깊은 아픔이 찾아온 날에는 그저 흘러가는 마음을 가만히 보듬어 주는 시간도 필요하답니다.",
            "가슴 깊은 곳에서 차오른 눈물이 당신의 지친 마음을 깨끗이 씻어내어 주기를, 그리고 마음의 비가 곧 그치기를 바랍니다.",
            "울적하고 쓸쓸한 마음이 방 안을 채울 때, 당신의 소리 없는 한숨마저 따스하게 감싸 안아주고 싶네요. 많이 힘들었죠?",
            "마음의 온도가 조금 내려간 듯한 쓸쓸한 날이네요. 서두르지 않고 당신이 편안해질 때까지 곁에서 가만히 지켜줄게요."
        ],
        '분노': [
            "마음먹은 대로 되지 않아 속상하고, 억울하거나 화가 치밀어 오르는 고단한 순간이 당신을 지치게 만들었나 봐요.",
            "뜨겁게 타오르는 화를 마주하느라 마음의 에너지가 많이 소모되었을 텐데, 이제는 숨을 깊이 고르며 차분함을 되찾으시길 바라요.",
            "속상하고 원망스러운 감정이 불쑥 찾아와 당신의 고요한 마음을 흔들어 놓았군요. 당신의 화난 감정도 모두 소중한 마음의 신호랍니다.",
            "답답하고 끓어오르는 마음을 털어놓는 것만으로도 조금은 가벼워지셨기를 바라며, 다친 마음을 어루만져 드리고 싶습니다.",
            "날카로운 바람이 스치듯 마음이 요동친 하루였네요. 상처받은 마음의 앙금을 털어내고 편안한 휴식을 취할 수 있기를 응원해요."
        ],
        '두려움': [
            "앞날이 불투명하게 느껴지거나 두려움과 불안이 엄습할 때, 당신의 마음은 얼마나 떨리고 위태로웠을까요.",
            "어두운 밤길을 걷는 듯한 불안감이 몰려와도, 당신은 이미 스스로를 지켜낼 만큼 굳건하고 지혜로운 사람임을 기억해 주세요.",
            "막막하고 두려운 마음에 발걸음이 무거워질 때면 잠시 멈추어 서서 따뜻한 온기가 있는 곳에 마음을 기대어 보세요.",
            "이유 없는 불안이 소리 없이 찾아와 당신을 작아지게 만들었군요. 혼자가 아니니 걱정 마세요, 곧 괜찮아질 거예요.",
            "어둠 속에서 길을 잃은 듯한 초조함이 있었지만, 당신의 마음 안에는 언제나 길을 밝혀줄 작은 등불이 켜져 있답니다."
        ],
        '신뢰': [
            "주변의 소중한 이들과 깊은 믿음을 나누거나, 스스로를 굳건히 믿는 단단하고 흔들림 없는 하루를 보내셨군요.",
            "서로를 향한 따뜻한 지지와 믿음이 당신의 오늘을 든든하게 받쳐주어 참 온화하고 평온한 시간이 느껴집니다.",
            "세상이 나를 향해 웃어주는 듯한 안도감과 든든함 속에서, 당신의 마음이 한층 더 평화롭고 따스해 보여 참 기쁩니다.",
            "누군가를 신뢰하고 또 신뢰받는 일은 마음에 깊은 뿌리를 내리는 일이지요. 굳건하고 안정감 있는 하루를 보내셨네요.",
            "단단한 중심을 잡고 주변에 긍정적인 신뢰를 건넨 오늘, 당신의 그 든든하고 선한 영향력이 깊이 느껴집니다."
        ],
        '놀람': [
            "예상치 못한 신선한 자극이나 반가운 변화가 찾아와 오늘 하루가 유독 활기차고 특별하게 다채로웠겠네요!",
            "깜짝 놀랄 만한 일들로 마음이 톡 쏘는 탄산처럼 짜릿하게 요동친 신기하고 흥미진진한 날을 보내셨군요.",
            "예측할 수 없었던 선물 같은 순간들이 당신의 일상에 유쾌하고 놀라운 파동을 몰고 온 다이내믹한 하루였네요.",
            "갑작스러운 사건으로 가슴이 쿵 내려앉거나 깜짝 놀랐을 텐데, 새로운 에너지와 함께 평정을 찾아가길 바랄게요.",
            "익숙한 일상을 벗어나 예상 밖의 신비로운 조각들을 마주하며 호기심 가득하고 짜릿한 시간을 만끽하셨군요."
        ],
        '알수없음': [
            "다양한 생각들이 머릿속을 스치고 지나가며, 한 가지 단어로 쉽게 정의하기 어려운 오묘하고 깊은 날이었네요.",
            "차분하고 잔잔한 물결처럼 평온하게 흘러간 오늘, 특별한 요동 없이 스스로를 돌아볼 수 있는 고요한 하루였습니다.",
            "때로는 감정의 이름표를 굳이 붙이지 않아도 괜찮아요. 그저 존재 자체로 충분히 온전하고 아름다운 오늘을 보내셨습니다.",
            "여러 마음이 복합적으로 얽혀 복잡미묘하게 다가온 오늘 하루도 당신이 묵묵히 잘 걸어왔음에 따뜻한 격려를 보냅니다.",
            "특별한 굴곡 없이 물 흐르듯 잔잔하게 지나간 시간 속에서, 편안하고 무탈한 쉼표 하나를 마음에 꾹 찍어보세요."
        ]
    }
    
    # 해당 감정의 멘트 리스트에서 하나를 무작위 선택
    selected_intro = random.choice(empathy_templates.get(primary_emotion, empathy_templates['알수없음']))
    
    # 문맥 유도 멘트와 결합
    full_message = f"{selected_intro} 그래서 회원님의 마음에 따뜻한 온기를 채워줄 콘텐츠를 이렇게 추천해 드려요."
    
    return Response({
        'has_diaries': True,
        'primary_emotion': primary_emotion,
        'empathy_message': full_message
    }, status=status.HTTP_200_OK)


# ===== 단일 일기 상세 조회 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="단일 일기 상세 조회",
    operation_description="지정된 일기 ID를 받아와 본문, 날씨, 작성 시간, 이미지, 그리고 세부 감정 분석 결과를 조회하여 반환합니다. 보안을 위해 타인의 일기는 조회할 수 없습니다.",
    security=[{'Token': []}],
    responses={
        200: openapi.Response('조회 성공', DiarySerializer),
        404: '일기를 찾을 수 없거나 접근 권한 없음',
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_diary_detail(request, diary_id):
    try:
        diary = Diary.objects.select_related('emotion').get(id=diary_id, user=request.user)
    except Diary.DoesNotExist:
        return Response({'message': '해당 일기를 찾을 수 없거나 접근 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
    serializer = DiarySerializer(diary)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ===== 유저 일기 목록 조회 API =====
@swagger_auto_schema(
    method='get',
    operation_summary="유저 일기 목록 조회",
    operation_description="현재 로그인한 사용자가 작성한 모든 일기 리스트를 최신 작성 순서대로 정렬하여 반환합니다.",
    security=[{'Token': []}],
    responses={
        200: openapi.Response('목록 조회 성공', DiarySerializer(many=True)),
        401: '인증되지 않은 사용자'
    }
)
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_diary_list(request):
    diaries = Diary.objects.filter(user=request.user).select_related('emotion')
    serializer = DiarySerializer(diaries, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)