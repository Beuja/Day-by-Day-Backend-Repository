import json
import os
import math
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

# 💡 [핵심 해결] 실시간으로 점수를 재계산하여 인스턴스에 붙여주는 도우미 함수
def _attach_scores(instances, diary_obj, mode, is_movie=False):
    if not instances:
        return instances
        
    raw_e = getattr(diary_obj, 'emotion', None)
    u_vec = [
        getattr(raw_e, 'joy', 0.0), getattr(raw_e, 'sadness', 0.0), 
        getattr(raw_e, 'anger', 0.0), getattr(raw_e, 'fear', 0.0), 
        getattr(raw_e, 'trust', 0.0), getattr(raw_e, 'surprise', 0.0)
    ]
    
    if is_movie:
        from .recommend_music_movie.recommend_movie import _get_target_emotion_vector, _get_direction_weights, _calculate_euclidean, _calculate_cosine, build_6d_emotion_vector
    else:
        from .recommend_music_movie.recommend_music import _get_target_emotion_vector, _get_direction_weights, _calculate_euclidean, _calculate_cosine, build_6d_emotion_vector
    
    target_vec = _get_target_emotion_vector(u_vec, mode)
    target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
    w_vec = _get_direction_weights(u_vec, mode)

    if mode == 'maintain': alpha = 0.90
    elif mode == 'amplification': alpha = 0.10
    else: alpha = 0.50

    for item in instances:
        b_vec = [
            getattr(item, 'joy', 0.0), getattr(item, 'sadness', 0.0), 
            getattr(item, 'anger', 0.0), getattr(item, 'fear', 0.0), 
            getattr(item, 'trust', 0.0), getattr(item, 'surprise', 0.0)
        ]
        
        if sum(b_vec) < 0.01:
            if is_movie:
                raw_tags = [item.genre] if getattr(item, 'genre', None) else []
            else:
                raw_tags = getattr(item, 'tags', [])
                if isinstance(raw_tags, str):
                    raw_tags = raw_tags.replace("'", '"')
                    try: raw_tags = json.loads(raw_tags)
                    except: raw_tags = [raw_tags]
                elif not isinstance(raw_tags, list):
                    raw_tags = []
            b_vec = build_6d_emotion_vector(raw_tags)
            
        norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
        cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
        emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
        
        if is_movie:
            popularity = float(getattr(item, 'popularity', 0.0) or 0.0)
            popularity_score = min(1.0, popularity / 500.0)
        else:
            popularity = float(getattr(item, 'listeners', 0) or 0)
            popularity_score = min(1.0, popularity / 50000000.0)
            
        final_score = (emotion_score * 0.95) + ((1.0 - popularity_score) * 0.05)
        item.score = round(final_score, 4)
        
    return instances

def get_or_create_music_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj, mode=mode)
    saved_count = daily_rec.musics.count()

    if created or saved_count == 0 or saved_count < count:
        music_data = load_music_data()
        recommender = MusicEmotionRecommender()
        res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)
        
        music_instances = res.get('recommendations', [])
        is_fallback = res.get('is_fallback', False) 
        
        # 💡 [버그 1 수정] fallback 여부와 상관없이 무조건 저장! (빈 배열 방지)
        daily_rec.musics.set(music_instances)
            
    else:
        music_instances = list(daily_rec.musics.all()[:count])
        # 💡 [버그 2 수정] 이미 저장된 데이터를 POST 요청으로 불러올 때 score 부여!
        _attach_scores(music_instances, diary_obj, mode, is_movie=False)
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

        # 💡 [버그 1 수정] fallback 여부와 상관없이 무조건 저장! (빈 배열 방지)
        daily_rec.movies.set(movie_instances)

    else:
        movie_instances = list(daily_rec.movies.all()[:count])
        # 💡 [버그 2 수정] 이미 저장된 데이터를 POST 요청으로 불러올 때 score 부여!
        _attach_scores(movie_instances, diary_obj, mode, is_movie=True)
        is_fallback = False
    
    return movie_instances, is_fallback

def get_saved_music_metadata(diary_obj):
    daily_recs = DailyRecommended.objects.filter(diary=diary_obj).prefetch_related('musics')
    for rec in daily_recs:
        # 💡 GET(조회) 할 때도 score를 0이 아니라 실제 점수로 계산하여 덧붙입니다.
        _attach_scores(rec.musics.all(), diary_obj, rec.mode, is_movie=False)
    return daily_recs

def get_saved_movie_metadata(diary_obj):
    daily_recs = DailyRecommended.objects.filter(diary=diary_obj).prefetch_related('movies')
    for rec in daily_recs:
        # 💡 GET(조회) 할 때도 score를 0이 아니라 실제 점수로 계산하여 덧붙입니다.
        _attach_scores(rec.movies.all(), diary_obj, rec.mode, is_movie=True)
    return daily_recs