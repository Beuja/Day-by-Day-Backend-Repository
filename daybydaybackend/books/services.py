# books/services.py
import math
from .models import Book

def _calculate_target_coordinates(v, a, mode):
    """추천 mode에 따른 타겟 감정 좌표 결정"""
    # shift
    if mode == 'shift':
        return (-0.5, -0.5) if v >= 0 else (0.5, 0.5)
    
    # amplification
    if mode == 'amplification':
        target_v = max(-1.0, min(1.0, v * 1.5))
        target_a = max(-1.0, min(1.0, a * 1.5))
        return target_v, target_a
    
    # maintain(기본값)
    return v, a

def _get_distance(v1, a1, v2, a2):
    """두 감정 좌표 사이 유클리드 거리 계산"""
    return math.sqrt((v1 - v2)**2 + (a1 - a2)**2)

def recommend_books(v, a, mode, count):
    """
    감정 벡터를 기반으로 추천 도서 목록 반환
    """
    target_v, target_a = _calculate_target_coordinates(v, a, mode)
    
    candidate_books = Book.objects.filter(valence__isnull=False, arousal__isnull=False)
    
    recommended_books = sorted(
        candidate_books,
        key=lambda book: _get_distance(target_v, target_a, book.valence, book.arousal)
    )

    return recommended_books[:count]
