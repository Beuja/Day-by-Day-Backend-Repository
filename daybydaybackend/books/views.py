# books/views.py
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
    operation_summary="감정 기반 도서 추천",
    operation_description="사용자의 감정 수치(valence, arousal)를 기반으로 추천 도서 목록을 반환합니다.",
    security=[{'Token': []}],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'valence': openapi.Schema(type=openapi.TYPE_NUMBER, description='유쾌도 (-1.0 ~ 1.0)'),
            'arousal': openapi.Schema(type=openapi.TYPE_NUMBER, description='각성도 (-1.0 ~ 1.0)'),
            'mode': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['maintain', 'shift', 'amplification'],
                description='추천 전략 (유지/반전/강화)'
            ),
            'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='추천 도서 개수 (기본값: 3)')
        },
        required=['valence', 'arousal']
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
def recommend_books(request):
    """감정 벡터를 기반으로 도서 추천"""
    valence = request.data.get('valence')
    arousal = request.data.get('arousal')
    mode = request.data.get('mode', 'maintain')
    count = request.data.get('count', 3)
    
    # 입력값 검증
    try:
        valence = float(valence)
        arousal = float(arousal)
        count = int(count)
        
        if not (-1.0 <= valence <= 1.0 and -1.0 <= arousal <= 1.0):
            return Response(
                {'message': 'valence와 arousal은 -1.0에서 1.0 사이의 값이어야 합니다.'},
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
