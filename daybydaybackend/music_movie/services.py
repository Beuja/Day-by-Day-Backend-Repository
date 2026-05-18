import json
import os

from .recommend_music_movie.recommend_by_emotion import (
    EmotionRecommender,
)

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


def convert_emotion_vector_to_russell(emotion_vector: dict) -> tuple:
    """
    10차원 감정 벡터를 Russell의 2차원 모델로 변환

    Args:
        emotion_vector: 10차원 감정 벡터 딕셔너리

    Returns:
        (valence, arousal) 튜플
    """
    valence = (
        emotion_vector.get('joy', 0) * 1.0 +
        emotion_vector.get('romance', 0) * 0.7 +
        emotion_vector.get('calmness', 0) * 0.4 +
        emotion_vector.get('sadness', 0) * -1.0 +
        emotion_vector.get('anger', 0) * -0.8 +
        emotion_vector.get('fear', 0) * -0.7 +
        emotion_vector.get('darkness', 0) * -0.6
    )

    arousal = (
        emotion_vector.get('energy', 0) * 1.0 +
        emotion_vector.get('anger', 0) * 0.7 +
        emotion_vector.get('fear', 0) * 0.6 +
        emotion_vector.get('dreaminess', 0) * -0.2 +
        emotion_vector.get('calmness', 0) * -0.7
    )

    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))

    return (round(valence, 2), round(arousal, 2))


def recommend_music(valence: float, arousal: float, mode: str = 'maintain', count: int = 5):
    recommender = EmotionRecommender()

    music_data = load_music_data()
    rec = recommender.recommend_music(
        {'valence': valence, 'arousal': arousal},
        music_data,
        top_n=count
    )
    return rec


def recommend_movies(valence: float, arousal: float, mode: str = 'maintain', count: int = 5):
    recommender = EmotionRecommender()

    movie_data = load_movie_data()
    rec = recommender.recommend_movies(
        {'valence': valence, 'arousal': arousal},
        movie_data,
        top_n=count
    )
    return rec
