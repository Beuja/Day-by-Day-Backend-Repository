# books/views.py
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Book
from .services import recommend_books
from .serializers import BookSerializer, RecommendRequestSerializer

from daybydaybackend.diary.models import DiaryEmotion

class BookViewSet(viewsets.ModelViewSet): 
    queryset = Book.objects.all()
    serializer_class = BookSerializer

@swagger_auto_schema(
    method='post',
    operation_summary="감정 기반 도서 추천",
    operation_description="사용자의 감정 데이터를 기반으로 맞춤형 도서를 추천합니다.",
    request_body=RecommendRequestSerializer,
    responses={
        200: openapi.Response('도서 추천 완료', BookSerializer(many=True)),
        400: '잘못된 요청 (감정 정보 누락 또는 잘못된 count 포맷)'
    }
)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_books_views(request):
    user_emotion = request.data.get('emotion')
    mode = request.data.get('mode')
    diary_id = request.data.get('diary_id')

    if not diary_id:
        return Response(
            {'message': 'diary_id가 필요합니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        count = int(request.data.get('count', 3))
    except (TypeError, ValueError):
        return Response(
            {'message': 'count가 유효한 숫자가 아닙니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user_emotion:
        return Response(
            {'message': '사용자 감정 정보가 필요합니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        diary = Diary.objects.get(id=diary_id)
    except Diary.DoesNotExist:
        return Response(
            {'message': '해당 일기를 찾을 수 없습니다.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    recommended_books_list = recommend_books(
        user_emotion=user_emotion,
        mode=mode,
        count=count
    )

    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary)
    daily_rec.recommended_books.set(recommended_books_list) # set : 추천 다시 요청했을 때 기존 목록 덮어씀, 필요시 add로 변경 

    response_serializer = BookSerializer(recommended_books_list, many=True)
    
    return Response({
            "status": "success",
            "message": "도서 추천 완료",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)

    """
    serializer = RecommendRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    diary_id = serializer.validated_data.get('diary_id')
    mode = serializer.validated_data.get('mode')
    count = serializer.validated_data.get('count')

    try:
        emotion = DiaryEmotion.objects.get(diary_id=diary_id, diary__user=request.user)
        valence = emotion.valence
        arousal = emotion.arousal
    except DiaryEmotion.DoesNotExist:
        return Response(
            {'message': '해당 일기의 감정 분석 결과가 존재하지 않습니다.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
 
    # 추천 도서 조회
    books = recommend_books(valence, arousal, mode, count)
    serialized_books = BookSerializer(books, many=True)
    
    return Response(
        {'books': serialized_books},
        status=status.HTTP_200_OK
    )
    """
