import json
import os
from diary.models import Diary, DailyRecommended
from music_movie.models import Music, Movie
from .recommend_music_movie.recommend_music import MusicEmotionRecommender
from .recommend_music_movie.recommend_movie import MovieEmotionRecommender

PACKAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommend_music_movie')

def load_json_file(file_name: str):
    path = os.path.join(PACKAGE_DIR, file_name)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_music_data():
    return load_json_file('music_database.json')

def load_movie_data():
    return load_json_file('movie_database.json')

def convert_emotion_to_6d_vector(emotion_vector: dict) -> dict:
    """
    입력받은 다양한 가중치 태그를 books 및 diary 앱과 정합성을 이루는
    6차원 기본 감정 벡터로 병합 및 정규화(0.0 ~ 1.0)합니다.
    """
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
    trust = (
        emotion_vector.get('trust', 0) * 1.0 +
        emotion_vector.get('calmness', 0) * 0.8 +
        emotion_vector.get('dreaminess', 0) * 0.4
    )
    surprise = (
        emotion_vector.get('surprise', 0) * 1.0 +
        emotion_vector.get('energy', 0) * 0.5
    )

    return {
        'joy': round(max(0.0, min(1.0, joy)), 2),
        'sadness': round(max(0.0, min(1.0, sadness)), 2),
        'anger': round(max(0.0, min(1.0, anger)), 2),
        'fear': round(max(0.0, min(1.0, fear)), 2),
        'trust': round(max(0.0, min(1.0, trust)), 2),
        'surprise': round(max(0.0, min(1.0, surprise)), 2),
    }

# --- 최초 추천 생성 및 ManyToMany 관계 자동 저장 ---
def get_or_create_music_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    """최초 요청 시 음악 추천을 연산하고, 통합 DailyRecommended 테이블 다대다 관계를 바인딩합니다."""
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    music_data = load_music_data()
    
    recommender = MusicEmotionRecommender()
    res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)
    
    # 추천된 track_id 목록에 해당하는 DB 실제 인스턴스들을 조회하여 ManyToManyField에 연결
    recommended_track_ids = [track['track_id'] for track in res['recommendations']]
    music_instances = Music.objects.filter(track_id__in=recommended_track_ids)
    
    daily_rec.music.set(music_instances)
    return res['recommendations']

def get_or_create_movie_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    """최초 요청 시 영화 추천을 연산하고, 통합 DailyRecommended 테이블 다대다 관계를 바인딩합니다."""
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    movie_data = load_movie_data()
    
    recommender = MovieEmotionRecommender()
    res = recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)
    
    recommended_movie_ids = [movie['movie_id'] for movie in res['recommendations']]
    movie_instances = Movie.objects.filter(movie_id__in=recommended_movie_ids)
    
    daily_rec.movies.set(movie_instances)
    return res['recommendations']

# --- 달력 클릭 시 DB 인스턴스 기반 매적 역참조 복원 기능 ---
def get_saved_music_metadata(diary_obj):
    """DailyRecommended 관계를 고속 정밀 탐색하여 저장된 음악 목록을 응답 포맷으로 복원합니다."""
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []
    
    # DB 인스턴스 목록 순회 가공
    return [
        {
            'track_id': music.track_id,
            'title': music.title,
            'artist': music.artist,
            'image_url': getattr(music, 'image_url', ''),
            'tags': music.tags if isinstance(music.tags, list) else []
        }
        for music in daily_rec.music.all()
    ]

def get_saved_movie_metadata(diary_obj):
    """DailyRecommended 관계를 고속 정밀 탐색하여 저장된 영화 목록을 응답 포맷으로 복원합니다."""
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []
    
    return [
        {
            'movie_id': movie.movie_id,
            'title': movie.title,
            'director': movie.director,
            'image_url': getattr(movie, 'image_url', ''),
            'tags': movie.tags if isinstance(movie.tags, list) else []
        }
        for movie in daily_rec.movies.all()
    ]