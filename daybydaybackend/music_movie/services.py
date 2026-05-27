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
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj, mode=mode)
    saved_count = daily_rec.musics.count()

    if created or saved_count == 0 or saved_count < count:
        music_data = load_music_data()
        recommender = MusicEmotionRecommender()
        res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)
        
        music_instances = res.get('recommendations', [])
        is_fallback = res.get('is_fallback', False) 
        
        # fallback이 아닐 때만 저장
        if not is_fallback:
            daily_rec.musics.set(music_instances)
            
    else:
        music_instances = daily_rec.musics.all()[:count]
        is_fallback = False
        
    return music_instances, is_fallback

def get_or_create_movie_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj, mode=mode)
    saved_count = daily_rec.movies.count()

    if created or saved_count == 0 or saved_count < count:
        movie_data = load_movie_data()
        for movie in movie_data:
            if isinstance(movie.get("genre"), list):
                movie["genre"] = ", ".join(movie["genre"])
        recommender = MovieEmotionRecommender()
        res = recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)

        movie_instances = res.get('recommendations', [])
        is_fallback = res.get('is_fallback', False)

        if not is_fallback:
            daily_rec.movies.set(movie_instances)

    else:
        movie_instances = daily_rec.movies.all()[:count]
        is_fallback = False
    
    return movie_instances, is_fallback

def get_saved_music_metadata(diary_obj):
    return DailyRecommended.objects.filter(diary=diary_obj).prefetch_related('musics')

def get_saved_movie_metadata(diary_obj):
    return DailyRecommended.objects.filter(diary=diary_obj).prefetch_related('movies')