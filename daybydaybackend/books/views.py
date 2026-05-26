# books/views.py
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404

from .models import Book
from .services import get_or_create_book_recommendation, get_saved_book_metadata
from .serializers import BookSerializer, ContentRecommendationRequestSerializer

from daybydaybackend.diary.models import Diary

class BookViewSet(viewsets.ModelViewSet): 
    queryset = Book.objects.all()
    serializer_class = BookSerializer


diary_id_path_parameter = openapi.Parameter(
    name='diary_id',
    in_=openapi.IN_PATH,
    description='추천 대상 일기 ID',
    type=openapi.TYPE_INTEGER,
    required=True,
)

@swagger_auto_schema(
    method='get',
    operation_summary='저장된 도서 추천 조회',
    operation_description='일기 상세에 저장된 도서 추천 결과를 복원해서 반환합니다. 음악/영화 추천과 동일한 방식으로 동작합니다.',
    manual_parameters=[diary_id_path_parameter],
    responses={
        200: openapi.Response('조회 성공', BookSerializer(many=True)),
        404: '해당 일기 또는 추천 결과를 찾을 수 없음'
    }
)
@swagger_auto_schema(
    method='post',
    operation_summary="감정 기반 도서 추천",
    operation_description='일기 감정 데이터를 기반으로 맞춤형 도서를 추천합니다. 요청 바디의 mode 파라미터를 통해 세 가지 추천 전략 중 하나를 사용할 수 있습니다.\n\n- maintain: 현재 사용자의 감정 상태를 차분하게 유지할 수 있는 도서를 추천합니다 (기본값).\n- shift: 우울하거나 분노할 때 반대되는 긍정적이고 밝은 감정으로 전환(Shift)할 수 있는 도서를 추천합니다.\n- amplification: 현재의 신나고 즐거운 감정을 극대화(Amplification)하고 고취시킬 수 있는 도서를 추천합니다.',
    request_body=ContentRecommendationRequestSerializer,
    responses={
        200: openapi.Response('도서 추천 완료', BookSerializer(many=True)),
        400: '잘못된 요청 (count 포맷 오류 등)'
    }
)
@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_books_views(request, diary_id):
    diary = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)

    if request.method == 'GET':
        books = get_saved_book_metadata(diary)
        serializer = BookSerializer(books, many=True)
        return Response({"recommendations": serializer.data}, status=status.HTTP_200_OK)

    req_serializer = ContentRecommendationRequestSerializer(data=request.data)
    req_serializer.is_valid(raise_exception=True)

    mode = req_serializer.validated_data.get('mode', 'maintain')
    count = req_serializer.validated_data.get('count', 3)

    raw_emotion = getattr(diary, 'emotion', None)
    user_6d_emotion = {
        'joy': getattr(raw_emotion, 'joy', 0.0),
        'sadness': getattr(raw_emotion, 'sadness', 0.0),
        'anger': getattr(raw_emotion, 'anger', 0.0),
        'fear': getattr(raw_emotion, 'fear', 0.0),
        'trust': getattr(raw_emotion, 'trust', 0.0),
        'surprise': getattr(raw_emotion, 'surprise', 0.0),
    }

    books = get_or_create_book_recommendation(diary, user_6d_emotion, mode, count)
    serializer = BookSerializer(books, many=True)
    return Response({"mode": mode, "recommendations": serializer.data}, status=status.HTTP_200_OK)
