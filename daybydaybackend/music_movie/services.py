import json
import os
from .models import SavedRecommendation
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

# --- 최초 추천 생성 및 자동 저장 파이프라인 ---
def get_or_create_music_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    """최초 요청 시 음악 추천을 연산하고 DB에 고유 ID 배열을 보관합니다."""
    saved_rec, created = SavedRecommendation.objects.get_or_create(diary=diary_obj)
    music_data = load_music_data()
    
    recommender = MusicEmotionRecommender()
    res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)
    
    # 영구 보관용 ID 배열 추출 및 업데이트
    saved_rec.recommended_music_ids = [track['track_id'] for track in res['recommendations']]
    saved_rec.save()
    return res['recommendations']

def get_or_create_movie_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    """최초 요청 시 영화 추천을 연산하고 DB에 고유 ID 배열을 보관합니다."""
    saved_rec, created = SavedRecommendation.objects.get_or_create(diary=diary_obj)
    movie_data = load_movie_data()
    
    recommender = MovieEmotionRecommender()
    res = recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)
    
    saved_rec.recommended_movie_ids = [movie['movie_id'] for movie in res['recommendations']]
    saved_rec.save()
    return res['recommendations']

# --- 달력 클릭 시 과거 데이터 역추적 복원 기능 ---
def get_saved_music_metadata(diary_obj):
    """과거 저장된 ID 배열을 기점으로 대중성 파싱 파일에서 제목, 이미지, 태그 정보를 역추적 복원합니다."""
    try:
        saved_rec = SavedRecommendation.objects.get(diary=diary_obj)
    except SavedRecommendation.DoesNotExist:
        return []
    
    music_data = load_music_data()
    id_maps = {track['track_id']: track for track in music_data}
    
    restored_list = []
    for m_id in saved_rec.recommended_music_ids:
        if m_id in id_maps:
            orig = id_maps[m_id]
            restored_list.append({
                'track_id': m_id,
                'title': orig.get('title'),
                'artist': orig.get('artist'),
                'image_url': orig.get('image_url', ''),
                'tags': orig.get('tags', [])
            })
    return restored_list

def get_saved_movie_metadata(diary_obj):
    """과거 저장된 ID 배열을 기점으로 영화 포스터, 타이틀 메타데이터를 역추적 복원합니다."""
    try:
        saved_rec = SavedRecommendation.objects.get(diary=diary_obj)
    except SavedRecommendation.DoesNotExist:
        return []
    
    movie_data = load_movie_data()
    id_maps = {movie['movie_id']: movie for movie in movie_data}
    
    restored_list = []
    for m_id in saved_rec.recommended_movie_ids:
        if m_id in id_maps:
            orig = id_maps[m_id]
            restored_list.append({
                'movie_id': m_id,
                'title': orig.get('title'),
                'director': orig.get('director'),
                'image_url': orig.get('image_url', ''),
                'tags': orig.get('tags', [])
            })
    return restored_list