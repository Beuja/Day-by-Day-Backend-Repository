import json
import os
from daybydaybackend.diary.models import Diary, DailyRecommended
from daybydaybackend.music_movie.models import Music, Movie
from .recommend_music_movie.recommend_music import MusicEmotionRecommender
from .recommend_music_movie.recommend_movie import MovieEmotionRecommender

PACKAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommend_music_movie')

_cached_music_data = None
_cached_movie_data = None

def load_music_data():
    global _cached_music_data
    if _cached_music_data is None:
        db_music = Music.objects.all().values(
            'id', 'title', 'artist', 'source_tag', 'listeners', 
            'playcount', 'image_url', 'tags', 
            'valence', 'arousal', 'joy', 'sadness', 'anger', 'fear', 'trust', 'surprise'
        )
        _cached_music_data = []
        for m in db_music:
            m['track_id'] = m['id']
            _cached_music_data.append(m)
    return _cached_music_data

def load_movie_data():
    global _cached_movie_data
    if _cached_movie_data is None:
        db_movie = Movie.objects.all().values(
            'tmdb_id', 'title', 'genre', 'overview', 'vote_average', 
            'vote_count', 'popularity', 'release_date', 'poster_path', 
            'valence', 'arousal', 'joy', 'sadness', 'anger', 'fear', 'trust', 'surprise'
        )
        _cached_movie_data = []
        for m in db_movie:
            m['movie_id'] = m['tmdb_id']
            _cached_movie_data.append(m)
    return _cached_movie_data

def clear_content_cache():
    global _cached_music_data, _cached_movie_data
    _cached_music_data = None
    _cached_movie_data = None

def convert_emotion_to_6d_vector(emotion_vector: dict) -> dict:
    joy = emotion_vector.get('joy', 0) * 1.0 + emotion_vector.get('romance', 0) * 0.6
    sadness = emotion_vector.get('sadness', 0) * 1.0 + emotion_vector.get('darkness', 0) * 0.5
    anger = emotion_vector.get('anger', 0) * 1.0
    fear = emotion_vector.get('fear', 0) * 1.0 + emotion_vector.get('darkness', 0) * 0.3
    trust = emotion_vector.get('trust', 0) * 1.0 + emotion_vector.get('calmness', 0) * 0.8
    surprise = emotion_vector.get('surprise', 0) * 1.0 + emotion_vector.get('energy', 0) * 0.5
    return {
        'joy': round(max(0.0, min(1.0, joy)), 2), 'sadness': round(max(0.0, min(1.0, sadness)), 2),
        'anger': round(max(0.0, min(1.0, anger)), 2), 'fear': round(max(0.0, min(1.0, fear)), 2),
        'trust': round(max(0.0, min(1.0, trust)), 2), 'surprise': round(max(0.0, min(1.0, surprise)), 2),
    }

def get_or_create_music_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    music_data = load_music_data()
    recommender = MusicEmotionRecommender()
    res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)
    music_instances = res['recommendations']
    daily_rec.music.set(music_instances)
    
    # 💡 [버그 수정] 추천을 생성(POST)할 때 사용된 mode를 명시적으로 DB에 저장합니다!
    daily_rec.mode = mode
    daily_rec.save()
    
    return music_instances

def get_or_create_movie_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    movie_data = load_movie_data()
    for movie in movie_data:
        if isinstance(movie.get("genre"), list):
            movie["genre"] = ", ".join(movie["genre"])
    recommender = MovieEmotionRecommender()
    res = recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)
    movie_instances = res['recommendations']
    daily_rec.movies.set(movie_instances)
    
    # 💡 [버그 수정] 추천을 생성(POST)할 때 사용된 mode를 명시적으로 DB에 저장합니다!
    daily_rec.mode = mode
    daily_rec.save()
    
    return movie_instances

def get_saved_music_metadata(diary_obj):
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []
    
    mode = getattr(daily_rec, 'mode', 'maintain')
    raw_e = getattr(diary_obj, 'emotion', None)
    u_vec = [getattr(raw_e, 'joy', 0.0), getattr(raw_e, 'sadness', 0.0), getattr(raw_e, 'anger', 0.0), getattr(raw_e, 'fear', 0.0), getattr(raw_e, 'trust', 0.0), getattr(raw_e, 'surprise', 0.0)]
    
    from .recommend_music_movie.recommend_music import _get_target_emotion_vector, _get_direction_weights, _calculate_euclidean, _calculate_cosine, build_6d_emotion_vector
    import math
    
    target_vec = _get_target_emotion_vector(u_vec, mode)
    target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
    w_vec = _get_direction_weights(u_vec, mode)
    
    if mode == 'maintain': alpha = 0.90
    elif mode == 'amplification': alpha = 0.10
    else: alpha = 0.50
    
    restored_music = []
    for music in daily_rec.music.all():
        b_vec = [getattr(music, 'joy', 0.0), getattr(music, 'sadness', 0.0), getattr(music, 'anger', 0.0), getattr(music, 'fear', 0.0), getattr(music, 'trust', 0.0), getattr(music, 'surprise', 0.0)]
        raw_tags = music.tags if isinstance(music.tags, list) else []
        if sum(b_vec) < 0.01:
            b_vec = build_6d_emotion_vector(raw_tags)
            
        norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
        cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
        emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
        
        popularity = float(getattr(music, 'listeners', 0) or 0)
        popularity_score = min(1.0, popularity / 50000000.0)
        final_score = (emotion_score * 0.95) + ((1.0 - popularity_score) * 0.05)
        
        restored_music.append({
            'track_id': music.id,
            'title': music.title,
            'artist': getattr(music, 'artist', ''),
            'image_url': getattr(music, 'image_url', ''),
            'tags': raw_tags,
            'score': round(final_score, 4)
        })
    restored_music.sort(key=lambda x: x['score'])
    return restored_music

def get_saved_movie_metadata(diary_obj):
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []
        
    mode = getattr(daily_rec, 'mode', 'maintain')
    raw_e = getattr(diary_obj, 'emotion', None)
    u_vec = [getattr(raw_e, 'joy', 0.0), getattr(raw_e, 'sadness', 0.0), getattr(raw_e, 'anger', 0.0), getattr(raw_e, 'fear', 0.0), getattr(raw_e, 'trust', 0.0), getattr(raw_e, 'surprise', 0.0)]
    
    from .recommend_music_movie.recommend_movie import _get_target_emotion_vector, _get_direction_weights, _calculate_euclidean, _calculate_cosine, build_6d_emotion_vector
    import math
    
    target_vec = _get_target_emotion_vector(u_vec, mode)
    target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
    w_vec = _get_direction_weights(u_vec, mode)

    if mode == 'maintain': alpha = 0.90
    elif mode == 'amplification': alpha = 0.10
    else: alpha = 0.50

    restored_movies = []
    for movie in daily_rec.movies.all():
        b_vec = [getattr(movie, 'joy', 0.0), getattr(movie, 'sadness', 0.0), getattr(movie, 'anger', 0.0), getattr(movie, 'fear', 0.0), getattr(movie, 'trust', 0.0), getattr(movie, 'surprise', 0.0)]
        movie_tags = [movie.genre] if movie.genre else []
        if sum(b_vec) < 0.01:
            b_vec = build_6d_emotion_vector(movie_tags)
            
        norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
        cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
        emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
        
        popularity = float(getattr(movie, 'popularity', 0.0) or 0.0)
        popularity_score = min(1.0, popularity / 500.0)
        final_score = (emotion_score * 0.95) + ((1.0 - popularity_score) * 0.05)
        
        restored_movies.append({
            'movie_id': movie.tmdb_id,
            'title': movie.title,
            'director': getattr(movie, 'director', ''),
            'image_url': movie.poster_path if movie.poster_path else '',
            'tags': movie_tags,
            'score': round(final_score, 4)
        })
    restored_movies.sort(key=lambda x: x['score'])
    return restored_movies