# music_movie/services.py
import json
import os

# 쪼개진 두 파일에서 각각의 Recommender 임포트
from .recommend_music_movie.recommend_music import MusicEmotionRecommender
from .recommend_music_movie.recommend_movie import MovieEmotionRecommender

PACKAGE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'recommend_music_movie'
)


def load_json_file(file_name: str):
    path = os.path.join(PACKAGE_DIR, file_name)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_music_data():
    return load_json_file('music_database.json')


def load_movie_data():
    return load_json_file('movie_database.json')


# daybydaybackend/music_movie/services.py

def convert_emotion_to_6d_vector(emotion_vector: dict) -> dict:
    """
    입력받은 감정/태그 딕셔너리를
    6차원 기본 감정 벡터(joy, sadness, anger, fear, trust, surprise)로 변환하고 정규화합니다.
    """
    ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
    
    # 1. 시스템 내 다양한 가중치 태그들을 6대 핵심 감정선으로 병합 연산
    joy = (
        emotion_vector.get('joy', 0) * 1.0 +
        emotion_vector.get('romance', 0) * 0.6
    )
    sadness = (
        emotion_vector.get('sadness', 0) * 1.0 +
        emotion_vector.get('darkness', 0) * 0.5
    )
    anger = (
        emotion_vector.get('anger', 0) * 1.0
    )
    fear = (
        emotion_vector.get('fear', 0) * 1.0 +
        emotion_vector.get('darkness', 0) * 0.3
    )
    # trust 혹은 유사 평온 태그 가중치 병합 (calmness 등 프로젝트 메타에 매칭)
    trust = (
        emotion_vector.get('trust', 0) * 1.0 +
        emotion_vector.get('calmness', 0) * 0.8 +
        emotion_vector.get('dreaminess', 0) * 0.4
    )
    surprise = (
        emotion_vector.get('surprise', 0) * 1.0 +
        emotion_vector.get('energy', 0) * 0.5
    )

    # 2. 6차원 스코어들의 범위를 0.0 ~ 1.0 사이로 안전하게 Clamping (정규화)
    result_vector = {
        'joy': max(0.0, min(1.0, joy)),
        'sadness': max(0.0, min(1.0, sadness)),
        'anger': max(0.0, min(1.0, anger)),
        'fear': max(0.0, min(1.0, fear)),
        'trust': max(0.0, min(1.0, trust)),
        'surprise': max(0.0, min(1.0, surprise))
    }

    # 소수점 2자리 혹은 4자리 반올림 처리하여 일관성 유지
    return {k: round(v, 2) for k, v in result_vector.items()}


# music_movie/services.py 수정 가이드 부분
def recommend_music(user_emotion: dict, mode: str = 'maintain', count: int = 5):
    recommender = MusicEmotionRecommender()
    music_data = load_music_data()
    # 인자값 포맷을 매칭하여 넘겨줍니다.
    return recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)

def recommend_movies(user_emotion: dict, mode: str = 'maintain', count: int = 5):
    recommender = MovieEmotionRecommender()
    movie_data = load_movie_data()
    # 인자값 포맷을 매칭하여 넘겨줍니다.
    return recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)