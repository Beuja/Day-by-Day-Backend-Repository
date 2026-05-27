# books/services.py

# import math
import numpy as np
from numpy.linalg import norm
from .models import Book
from django.db.models import Q
from daybydaybackend.diary.models import DailyRecommended

# 6가지 기본 감정 기반 도서 추천 서비스
def recommend_books(user_emotion: dict, mode: str = 'maintain', count: int = 3, user=None):
    # 계산을 위해 리스트 형태로 변경
    ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
    u_vec = np.array([user_emotion.get(key, 0.0) for key in ordered_keys])
    
    # 타겟 벡터 설정
    target_vec = _get_target_emotion(u_vec, mode)

    # 태그 0,0,0,0,0,0,0,0 인 책은 추천에서 제외 (리뷰 부족)
    all_books = Book.objects.filter(
        ~Q(valence=0.0) & ~Q(arousal=0.0) 
        & ~Q(joy=0.0) & ~Q(sadness=0.0) & ~Q(anger=0.0) & ~Q(fear=0.0) & ~Q(trust=0.0) & ~Q(surprise=0.0),
        link__isnull=False, joy__isnull=False
    )

    # 1. '싫어요' 한 책은 후보군에서 원천 제외 (Hard Filtering)
    if user and user.is_authenticated:
        from daybydaybackend.diary.models import UserFeedback
        disliked_isbns = UserFeedback.objects.filter(user=user, is_like=False, book__isnull=False).values_list('book__isbn', flat=True)
        all_books = all_books.exclude(isbn__in=disliked_isbns)

    # 2. 누적 '좋아요' 피드백을 기반으로 개인화 가중치(Beta) 및 타겟 벡터(V_target) 보정
    if user and user.is_authenticated:
        from daybydaybackend.diary.models import UserFeedback
        likes = UserFeedback.objects.filter(user=user, is_like=True)
        likes_count = likes.count()

        if likes_count > 0:
            if likes_count <= 4:
                beta = 0.15
            elif likes_count <= 9:
                beta = 0.30
            else:
                beta = 0.40

            # 모든 콘텐츠(책, 음악, 영화) 종합 선호도 프로필 계산
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
                v_profile = np.array([
                    joy_sum / vector_count,
                    sadness_sum / vector_count,
                    anger_sum / vector_count,
                    fear_sum / vector_count,
                    trust_sum / vector_count,
                    surprise_sum / vector_count
                ])
                # 타겟 감정 벡터 보정: V_target = (1 - beta) * target_vec + beta * V_profile
                target_vec = (1.0 - beta) * target_vec + beta * v_profile

    t_norm = norm(target_vec)
    if t_norm == 0:
        t_norm = 1e-9

    filtered_and_scored = []
    fallback_list = []

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

        pure_distance = np.sqrt(np.sum((target_vec - b_vec) ** 2))
        norm_euclidean = _calculate_euclidean(target_vec, b_vec)
        cosine_dist = _calculate_cosine(target_vec, b_vec, t_norm)

        final_score = (alpha * norm_euclidean) + ((1.0 - alpha) * cosine_dist)
        
        # 임계값 내에 있는 콘텐츠만 filtered_and_scored에 추가
        if pure_distance <= radius_limit:
            filtered_and_scored.append((final_score, book)) 

        fallback_list.append((final_score, book, pure_distance))

    if len(filtered_and_scored) >= count:
        filtered_and_scored.sort(key=lambda x: x[0])
        return [item[1] for item in filtered_and_scored[:count]], False

    # 추천 콘텐츠 수 < count 일 떄
    fallback_list.sort(key=lambda x: x[2])
    return [item[1] for item in fallback_list[:count]], True


def get_or_create_book_recommendation(diary_obj, user_emotion: dict, mode: str, count: int, user=None):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj, mode=mode)
    saved_count = daily_rec.books.count()

    if created or saved_count == 0 or saved_count < count:
        recommended_books, is_fallback = recommend_books(user_emotion=user_emotion, mode=mode, count=count, user=user)
        # fallback 아닐 때만 저장
        if not is_fallback:
            daily_rec.books.set(recommended_books)
    
    else:
        recommended_books = daily_rec.books.all()[:count]
        is_fallback = False
        
    return recommended_books, is_fallback


def get_saved_book_metadata(diary_obj):
    return DailyRecommended.objects.filter(diary=diary_obj).prefetch_related('books')

def _calculate_euclidean(t_vec: np.ndarray, b_vec: np.ndarray) -> float:
    # 가중 유클리드 거리 계산 및 정규화 (0~1 사이)
    ecuclidean_dist = np.sqrt(np.sum((t_vec - b_vec) ** 2))
    max_euclidean = np.sqrt(6.0)

    return ecuclidean_dist / max_euclidean

def _calculate_cosine(t_vec: np.ndarray, b_vec: np.ndarray, t_norm: float) -> float:
    # 코사인 유사도 계산
    b_norm = norm(b_vec)

    if b_norm == 0:
        b_norm = 1e-9

    cosine_sim = np.dot(t_vec, b_vec) / (t_norm * b_norm)
    return 1.0 - cosine_sim

def _get_target_emotion(u_vec: np.ndarray, mode: str) -> np.ndarray:
    # 추천 모드에 따라 추천의 기준이 될 목표 감정 벡터를 생성
    target_vec = u_vec.copy()
    
    if mode == 'shift':
        target_vec[1] *= 0.2  # sadness
        target_vec[2] *= 0.2  # anger
        target_vec[3] *= 0.2  # fear
        
        target_vec[0] = min(target_vec[0] + 0.5, 1.0)  # joy
        target_vec[4] = min(target_vec[4] + 0.4, 1.0)  # trust
        
    elif mode == 'amplification':
        target_vec[0] = min((target_vec[0] + 0.2) * 1.5, 1.0)  # joy
        target_vec[4] = min((target_vec[4] + 0.2) * 1.5, 1.0)  # trust
        
    # maintain 모드일 경우 그대로
    return target_vec