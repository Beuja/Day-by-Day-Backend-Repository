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
    request_body=RecommendRequestSerializer,
    responses={200: BookSerializer(many=True)}
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_books(request):
    user_emotion = request.data.get('emotion')
    mode = request.data.get('mode')
    count = int(request.data.get('count'))

    if not user_emotion:
        return Response(
            {'message': '사용자 감정 정보가 필요합니다.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    recommend_books = recommend_books(
        user_emotion=user_emotion,
        mode=mode,
        count=count
    )

    response_serializer = BookSerializer(recommend_books, many=True)
    
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
