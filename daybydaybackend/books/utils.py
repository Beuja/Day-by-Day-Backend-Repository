# books/utils.py
import math
from .models import Book


def get_book_recommendations(v, a, mode='maintain', count=3):
    """
    감정 벡터를 기반으로 추천 도서 목록 반환
    
    Args:
        v: valence 값 (-1.0 ~ 1.0)
        a: arousal 값 (-1.0 ~ 1.0)
        mode: 추천 전략 ('maintain', 'shift', 'amplification')
        count: 추천할 도서 개수
    
    Returns:
        추천 도서 QuerySet
    """
    target_v, target_a = v, a
    
    # shift mode: 감정 반대 방향으로 이동
    if mode == 'shift':
        if v >= 0:
            target_v, target_a = -0.5, -0.5
        else:
            target_v, target_a = 0.5, 0.5
    
    # amplification mode: 감정 강화
    elif mode == 'amplification':
        target_v = max(-1.0, min(1.0, v * 1.5))
        target_a = max(-1.0, min(1.0, a * 1.5))

    # 모든 도서에 대해 거리 계산
    all_books = Book.objects.filter(valence__isnull=False)
    scored_books = []
    
    for book in all_books:
        distance = math.sqrt((target_v - book.valence)**2 + (target_a - book.arousal)**2)
        scored_books.append((distance, book))
    
    scored_books.sort(key=lambda x: x[0])
    
    return [item[1] for item in scored_books[:count]]
