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
    사용자 일기 원본 감정 가중치 맵을 대포적인 6대 기본 정서선으로
    누락 없이 정규화 병합(0.0 ~ 1.0)합니다.
    """
    joy = emotion_vector.get('joy', 0) * 1.0 + emotion_vector.get('romance', 0) * 0.6
    sadness = emotion_vector.get('sadness', 0) * 1.0 + emotion_vector.get('darkness', 0) * 0.5
    anger = emotion_vector.get('anger', 0) * 1.0
    fear = emotion_vector.get('fear', 0) * 1.0 + emotion_vector.get('darkness', 0) * 0.3
    trust = emotion_vector.get('trust', 0) * 1.0 + emotion_vector.get('calmness', 0) * 0.8
    surprise = emotion_vector.get('surprise', 0) * 1.0 + emotion_vector.get('energy', 0) * 0.5

    return {
        'joy': round(max(0.0, min(1.0, joy)), 2),
        'sadness': round(max(0.0, min(1.0, sadness)), 2),
        'anger': round(max(0.0, min(1.0, anger)), 2),
        'fear': round(max(0.0, min(1.0, fear)), 2),
        'trust': round(max(0.0, min(1.0, trust)), 2),
        'surprise': round(max(0.0, min(1.0, surprise)), 2),
    }

# --- POST: 최초 일기 감정 수용 추천 연산 및 ManyToMany 적재 무결성 보장 ---
def get_or_create_music_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    music_data = load_music_data()
    
    recommender = MusicEmotionRecommender()
    res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)
    
    # 알고리즘 track_id 수치를 마스터 음악 테이블 고유 PK id와 싱크 얼라인
    recommended_track_ids = [track['track_id'] for track in res['recommendations']]
    music_instances = Music.objects.filter(id__in=recommended_track_ids)
    
    daily_rec.music.set(music_instances)
    return res['recommendations']

def get_or_create_movie_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    movie_data = load_movie_data()
    
    # 런타임 오류 방어: 영화 추천기 가동 전 한글 리스트 장르 포맷 우회 전처리 보정
    for movie in movie_data:
        if isinstance(movie.get("genre"), list):
            movie["genre"] = ", ".join(movie["genre"]) # 리스트를 문자열로 결합하여 알고리즘 호환성 충돌 제거
            
    recommender = MovieEmotionRecommender()
    res = recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)
    
    # 알고리즘 내부 movie_id 출력을 마스터 영화 테이블 프라이머리 키인 tmdb_id와 매핑
    recommended_movie_ids = [movie['movie_id'] for movie in res['recommendations']]
    movie_instances = Movie.objects.filter(tmdb_id__in=recommended_movie_ids)
    
    daily_rec.movies.set(movie_instances)
    return res['recommendations']

# --- GET: 달력 과거 내역 복원 역참조 메타데이터 변환 함수 ---
def get_saved_music_metadata(diary_obj):
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []
    
    return [
        {
            'track_id': music.id,  # 원본 테이블 primary key
            'title': music.title,
            'artist': music.artist if music.artist else '',
            'image_url': music.image_url if music.image_url else '',
            'tags': music.tags if isinstance(music.tags, list) else []
        }
        for music in daily_rec.music.all()
    ]

def get_saved_movie_metadata(diary_obj):
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []
        
    restored_movies = []
    for movie in daily_rec.movies.all():
        # 데이터베이스의 한글 장르 텍스트/배열을 유연하게 리스트 묶음 처리
        movie_tags = [movie.genre] if movie.genre else []
        
        restored_movies.append({
            'movie_id': movie.tmdb_id,  # 원본 고유 식별자 PK 반환
            'title': movie.title,
            'director': getattr(movie, 'director', ''),
            'image_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else '',
            'tags': movie_tags
        })
    return restored_movies