# music_movie/services.py
import math
from .models import Music, Movie


def convert_emotion_vector_to_russell(emotion_vector: dict) -> tuple:
    """
    10차원 감정 벡터를 Russell의 2차원 모델로 변환
    
    Args:
        emotion_vector: 10차원 감정 벡터 딕셔너리
    
    Returns:
        (valence, arousal) 튜플
    """
    valence = (
        emotion_vector.get("joy", 0) * 1.0 +
        emotion_vector.get("romance", 0) * 0.7 +
        emotion_vector.get("calmness", 0) * 0.4 +
        emotion_vector.get("sadness", 0) * -1.0 +
        emotion_vector.get("anger", 0) * -0.8 +
        emotion_vector.get("fear", 0) * -0.7 +
        emotion_vector.get("darkness", 0) * -0.6
    )

    arousal = (
        emotion_vector.get("energy", 0) * 1.0 +
        emotion_vector.get("anger", 0) * 0.7 +
        emotion_vector.get("fear", 0) * 0.6 +
        emotion_vector.get("dreaminess", 0) * -0.2 +
        emotion_vector.get("calmness", 0) * -0.7
    )

    # 범위 제한
    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))

    return (round(valence, 2), round(arousal, 2))


def get_target_emotion(valence: float, arousal: float, mode: str) -> tuple:
    """
    현재 감정과 전략에 따라 목표 감정 벡터 결정
    
    Args:
        valence: 현재 유쾌도
        arousal: 현재 각성도
        mode: 전략 ('maintain', 'shift', 'amplify', 'release', 'energize')
    
    Returns:
        (target_valence, target_arousal) 튜플
    """
    if mode == 'maintain':
        # 현재 감정 유지
        return (valence, arousal)
    
    elif mode == 'shift':
        # 감정 반전 (긍정→부정, 부정→긍정)
        return (-0.5 if valence >= 0 else 0.5, -0.5 if arousal >= 0 else 0.5)
    
    elif mode == 'amplify':
        # 긍정적 감정 강화
        target_v = min(1.0, valence + 0.2)
        target_a = min(1.0, arousal + 0.1)
        return (target_v, target_a)
    
    elif mode == 'release':
        # 부정적 긴장 해소
        target_v = min(0.3, valence + 0.5)
        target_a = max(-0.3, arousal - 0.4)
        return (target_v, target_a)
    
    elif mode == 'energize':
        # 우울 상태 활력 제공
        target_v = min(0.4, valence + 0.6)
        target_a = min(0.3, arousal + 0.5)
        return (target_v, target_a)
    
    return (valence, arousal)


def calculate_euclidean_distance(v1: tuple, v2: tuple) -> float:
    """두 감정 벡터 간의 유클리드 거리 계산"""
    return math.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)


def recommend_music(valence: float, arousal: float, mode: str = 'maintain', count: int = 5):
    """
    감정 벡터를 기반으로 음악 추천
    
    Returns:
        추천 음악 QuerySet
    """
    target_v, target_a = get_target_emotion(valence, arousal, mode)
    
    # 모든 음악 조회 (감정 벡터가 있는 것만)
    all_music = Music.objects.filter(valence__isnull=False)
    
    # 거리 계산
    scored_music = []
    for music in all_music:
        distance = calculate_euclidean_distance(
            (target_v, target_a),
            (music.valence, music.arousal)
        )
        scored_music.append((distance, music))
    
    scored_music.sort(key=lambda x: x[0])
    
    return [item[1] for item in scored_music[:count]]


def recommend_movies(valence: float, arousal: float, mode: str = 'maintain', count: int = 5):
    """
    감정 벡터를 기반으로 영화 추천
    
    Returns:
        추천 영화 QuerySet
    """
    target_v, target_a = get_target_emotion(valence, arousal, mode)
    
    # 모든 영화 조회 (감정 벡터가 있는 것만)
    all_movies = Movie.objects.filter(valence__isnull=False)
    
    # 거리 계산
    scored_movies = []
    for movie in all_movies:
        distance = calculate_euclidean_distance(
            (target_v, target_a),
            (movie.valence, movie.arousal)
        )
        scored_movies.append((distance, movie))
    
    scored_movies.sort(key=lambda x: x[0])
    
    return [item[1] for item in scored_movies[:count]]
