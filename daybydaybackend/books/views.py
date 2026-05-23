# books/views.py
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from daybydaybackend.diary.models import Diary
from .models import Book
from .utils import get_book_recommendations


class BookSerializer:
    """Book 모델을 위한 기본 직렬화 클래스"""
    @staticmethod
    def serialize(book):
        return {
            'isbn': book.isbn,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'description': book.description[:100] + '...' if len(book.description) > 100 else book.description,
            'valence': book.valence,
            'arousal': book.arousal,
        }


@swagger_auto_schema(
    method='post',
    operation_summary="일기 감정 기반 도서 추천",
    operation_description="diary_id로 선택한 일기의 감정 상태를 기준으로 추천 도서 목록을 반환합니다.",
    security=[{'Token': []}],
    manual_parameters=[
        openapi.Parameter(
            'diary_id',
            openapi.IN_PATH,
            description='추천에 사용할 일기 ID',
            type=openapi.TYPE_INTEGER,
            required=True,
        )
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'mode': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['maintain', 'shift', 'amplification'],
                description='어떤 감정 상태를 기준으로 도서를 추천할지'
            ),
            'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='추천할 도서 갯수 (기본값: 3)')
        },
        required=[]
    ),
    responses={
        200: openapi.Response('추천 성공', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'books': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                )
            }
        )),
        400: '잘못된 요청',
        401: '인증되지 않은 사용자'
    }
)
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_books(request, diary_id):
    """일기 감정을 기반으로 도서 추천"""
    diary_obj = get_object_or_404(Diary.objects.select_related('emotion'), id=diary_id, user=request.user)

    mode = request.data.get('mode', 'maintain')
    count = request.data.get('count', 3)

    emotion = getattr(diary_obj, 'emotion', None)
    valence = getattr(emotion, 'valence', 0.0) if emotion else 0.0
    arousal = getattr(emotion, 'arousal', 0.0) if emotion else 0.0

    # 입력값 검증
    try:
        count = int(count)
        
        if not (-1.0 <= valence <= 1.0 and -1.0 <= arousal <= 1.0):
            return Response(
                {'message': '일기 감정 값은 -1.0에서 1.0 사이의 값이어야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (TypeError, ValueError):
        return Response(
            {'message': '유효하지 않은 입력값입니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 추천 도서 조회
    books = get_book_recommendations(valence, arousal, mode, count)
    serialized_books = [BookSerializer.serialize(book) for book in books]
    
    return Response(
        {'books': serialized_books},
        status=status.HTTP_200_OK
    )
