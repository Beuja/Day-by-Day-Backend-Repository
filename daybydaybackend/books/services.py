# books/services.py

# import math
import numpy as np
from .models import Book

# 6가지 기본 감정 기반 도서 추천 서비스
def recommend_books(user_emotion: dict, mode: str = 'maintain', count: int = 3):
    # 계산을 위해 리스트 형태로 변경
    ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
    u_vec = np.array([user_emotion.get(key, 0.0) for key in ordered_keys])
    u_norm = norm(u_vec)
    if u_norm == 0:
        u_norm - 1e-9

    w_vec = _get_direction_weights(u_vec, mode)
    all_books = Book.objects.filter(joy__isnull=False)

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
        pure_distance = np.sqrt(np.sum((u_vec - b_vec) ** 2))

        if pure_distance <= radius_limit:
            norm_euclidean = _calculate_euclidean(u_vec, b_vec, w_vec)
            cosine_dist = _calculate_cosine(u_vec, b_vec, u_norm)

            # 최종 점수
            final_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
            filtered_and_scored.append((final_score, book))

    filtered_and_scored.sort(key=lambda x: x[0])

    return [item[1] for item in filtered_and_scored[:count]]

def _get_direction_weights(u_vec: np.ndarray, mode: str) -> np.ndarray:
    # 모드별 가중치 벡터 w 생성 함수
    weights = np.ones(6)
    
    if (mode == 'maintain'):
        return weights
    
    elif (mode == 'shift'):
        # sadness, anger, fear 패널티, joy, trust 인센티브, surprise 유지
        # 추후 조정
        weights[0] = 0.5    # joy
        weights[1] = 2.0    # sadness
        weights[2] = 2.0    # anger
        weights[3] = 2.0    # fear
        weights[4] = 0.5    # trust
        weights[5] = 1.0    # surprise

    elif (mode == 'amplification'):
        max_emotion_idx = np.argmax(u_vec)
        weights[max_emotion_idx] = 0.2

    return weights

def _calculate_euclidean(u_vec: np.ndarray, b_vec: np.ndarray, w_vec: np.ndarray) -> float:
    # 가중 유클리드 거리 계산 및 정규화 (0~1 사이)
    ecuclidean_dist = np.sqrt(np.sum(w_vec * (u_vec - b_vec) ** 2))
    max_euclidean = np.sqrt(np.sum(w_vec * (np.sum(w_vec * (1.0 ** 2)))))

    return ecuclidean_dist / max_euclidean

def _calculate_cosine(u_vec: np.ndarray, b_vec: np.ndarray, u_norm: float) -> float:
    # 코사인 유사도 계산
    b_norm = norm(b_vec)

    if b_norm == 0:
        b_norm = 1e-9

    cosine_sim = np.dot(u_vec, b_vec) / (u_norm * b_norm)
    return 1.0 - cosine_sim

"""
# 2차원 벡터 기반 (valence, arousal) 도서 추천 서비스
def _calculate_target_coordinates(v, a, mode):
    # 추천 mode에 따른 타겟 감정 좌표 결정
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
    # 두 감정 좌표 사이 유클리드 거리 계산
    return math.sqrt((v1 - v2)**2 + (a1 - a2)**2)

def recommend_books(v, a, mode, count):
    # 감정 벡터를 기반으로 추천 도서 목록 반환

    target_v, target_a = _calculate_target_coordinates(v, a, mode)
    
    candidate_books = Book.objects.filter(valence__isnull=False, arousal__isnull=False)
    
    recommended_books = sorted(
        candidate_books,
        key=lambda book: _get_distance(target_v, target_a, book.valence, book.arousal)
    )

    return recommended_books[:count]
"""