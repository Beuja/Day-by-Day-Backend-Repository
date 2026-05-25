# books/services.py

# import math
import numpy as np
from numpy.linalg import norm
from .models import Book
from django.db.models import Q
from daybydaybackend.diary.models import DailyRecommended

# 6가지 기본 감정 기반 도서 추천 서비스
def recommend_books(user_emotion: dict, mode: str = 'maintain', count: int = 3):
    # 계산을 위해 리스트 형태로 변경
    ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
    u_vec = np.array([user_emotion.get(key, 0.0) for key in ordered_keys])
    
    # 타겟 벡터 설정
    target_vec = _get_target_emotion(u_vec, mode)
    t_norm = norm(target_vec)
    if t_norm == 0:
        t_norm = 1e-9

    # 태그 0,0,0,0,0,0,0,0 인 책은 추천에서 제외 (리뷰 부족)
    all_books = Book.objects.filter(~Q(valence=0.0) & ~Q(arousal=0.0), link__isnull=False, joy__isnull=False)

    filtered_and_scored = []
    
    # 감정 범위 임계값
    if mode == 'maintain':
        radius_limit = 0.4
    elif mode == 'shift':
        radius_limit = 1.2
    elif mode == 'amplification':
        radius_limit = 0.8
    else:
        radius_limit = 0.7

    # 코사인 유사도&유클리드 거리 결합 가중치 (1에 가까울 수록 유클리드 거리 중시)
    alpha = 0.5

    for book in all_books:
        b_vec = np.array([
            book.joy, book.sadness, book.anger, 
            book.fear, book.trust, book.surprise
        ])
        # 순수 유클리드 거리
        pure_distance = np.sqrt(np.sum((target_vec - b_vec) ** 2))

        if pure_distance <= radius_limit:
            norm_euclidean = _calculate_euclidean(target_vec, b_vec)
            cosine_dist = _calculate_cosine(target_vec, b_vec, t_norm)

            # 최종 점수
            final_score = (alpha * norm_euclidean) + ((1.0 - alpha) * cosine_dist)
            filtered_and_scored.append((final_score, book))

    filtered_and_scored.sort(key=lambda x: x[0])

    # Fallback: if no books fall within the emotional radius (prevents empty recommendation for bland emotions)
    if not filtered_and_scored:
        fallback_list = []
        for book in all_books:
            b_vec = np.array([
                book.joy, book.sadness, book.anger, 
                book.fear, book.trust, book.surprise
            ])
            pure_distance = np.sqrt(np.sum((target_vec - b_vec) ** 2))
            norm_euclidean = _calculate_euclidean(target_vec, b_vec)
            cosine_dist = _calculate_cosine(target_vec, b_vec, t_norm)
            final_score = (alpha * norm_euclidean) + ((1.0 - alpha) * cosine_dist)
            
            fallback_list.append((final_score, book, pure_distance))
            
        # Sort by absolute emotional distance to yield the closest match
        fallback_list.sort(key=lambda x: x[2])
        return [item[1] for item in fallback_list[:count]], True

    return [item[1] for item in filtered_and_scored[:count]], False

def get_or_create_book_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, _ = DailyRecommended.objects.get_or_create(diary=diary_obj)
    recommended_books = recommend_books(user_emotion=user_emotion, mode=mode, count=count)
    daily_rec.books.set(recommended_books)
    return recommended_books


def get_saved_book_metadata(diary_obj):
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []

    return list(daily_rec.books.all())
def _calculate_euclidean(u_vec: np.ndarray, b_vec: np.ndarray) -> float:
    # 가중 유클리드 거리 계산 및 정규화 (0~1 사이)
    ecuclidean_dist = np.sqrt(np.sum((t_vec - b_vec) ** 2))
    max_euclidean = np.sqrt(6.0)

    return ecuclidean_dist / max_euclidean

def _calculate_cosine(u_vec: np.ndarray, b_vec: np.ndarray, u_norm: float) -> float:
    # 코사인 유사도 계산
    b_norm = norm(b_vec)

    if b_norm == 0:
        b_norm = 1e-9

    cosine_sim = np.dot(u_vec, b_vec) / (u_norm * b_norm)
    return 1.0 - cosine_sim

def _get_target_emotion(u_vec: np.ndarray, mode: str) -> np.ndarray:
    """추천 모드에 따라 추천의 기준이 될 목표 감정 벡터를 생성합니다."""
    target_vec = u_vec.copy()
    
    # 인덱스: 0=joy, 1=sadness, 2=anger, 3=fear, 4=trust, 5=surprise
    if mode == 'shift':
        # 부정적 감정은 완전히 지우지 않고 20% 수준으로 남겨 자연스러운 공감 유도
        target_vec[1] *= 0.2  # sadness
        target_vec[2] *= 0.2  # anger
        target_vec[3] *= 0.2  # fear
        
        # 긍정적 감정 증대 (최대 1.0 제한)
        target_vec[0] = min(target_vec[0] + 0.5, 1.0)  # joy
        target_vec[4] = min(target_vec[4] + 0.4, 1.0)  # trust
        
    elif mode == 'amplification':
        # 가장 지배적인 감정을 더욱 증폭
        max_idx = np.argmax(target_vec)
        target_vec[max_idx] = min(target_vec[max_idx] * 1.5, 1.0)
        
    # maintain 모드일 경우는 target_vec이 u_vec과 동일하게 유지됨
    return target_vec