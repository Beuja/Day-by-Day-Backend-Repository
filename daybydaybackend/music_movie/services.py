import json
import os

from .recommend_music_movie.recommend_by_emotion import EmotionRecommender
from .recommend_music_movie.recommend_music import MusicEmotionRecommender
from .recommend_music_movie.recommend_movie import MovieEmotionRecommender
from .models import Music, Movie
from daybydaybackend.diary.models import Diary, DailyRecommended

PACKAGE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data'
)


_cached_music_data = None
_cached_movie_data = None


def load_music_data():
    global _cached_music_data
    if _cached_music_data is None:
        db_music = Music.objects.all().values(
            'id', 'title', 'artist', 'source_tag', 'listeners', 
            'playcount', 'image_url', 'tags', 'emotion_vector', 
            'valence', 'arousal'
        )
        _cached_music_data = []
        for m in db_music:
            m['track_id'] = m['id']  # 추천 엔진 키 싱크
            _cached_music_data.append(m)
    return _cached_music_data


def load_movie_data():
    global _cached_movie_data
    if _cached_movie_data is None:
        db_movie = Movie.objects.all().values(
            'tmdb_id', 'title', 'genre', 'overview', 'vote_average', 
            'vote_count', 'popularity', 'release_date', 'poster_path', 
            'valence', 'arousal'
        )
        _cached_movie_data = []
        for m in db_movie:
            m['movie_id'] = m['tmdb_id']  # 추천 엔진 키 싱크
            _cached_movie_data.append(m)
    return _cached_movie_data


def clear_content_cache():
    """신규 콘텐츠 등록 시 메모리 캐시를 초기화할 수 있는 안전장치"""
    global _cached_music_data, _cached_movie_data
    _cached_music_data = None
    _cached_movie_data = None


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
    """임시 2D 추천 API입니다. 하위 호환용으로 유지되며 추후 제거될 수 있습니다."""
    recommender = EmotionRecommender()

    music_data = load_music_data()
    rec = recommender.recommend_music(
        {'valence': valence, 'arousal': arousal},
        music_data,
        top_n=count
    )
    return rec


def recommend_movies(valence: float, arousal: float, mode: str = 'maintain', count: int = 5):
    """임시 2D 추천 API입니다. 하위 호환용으로 유지되며 추후 제거될 수 있습니다."""
    recommender = EmotionRecommender()

    movie_data = load_movie_data()
    rec = recommender.recommend_movies(
        {'valence': valence, 'arousal': arousal},
        movie_data,
        top_n=count
    )
    return rec


# --- 최초 추천 생성 및 DailyRecommended ManyToMany 관계 자동 세팅 ---
def get_or_create_music_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    """최초 요청 시 음악 추천을 연산하고, 통합 DailyRecommended 테이블 다대다 관계를 바인딩합니다."""
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    music_data = load_music_data()

    recommender = MusicEmotionRecommender()
    res = recommender.recommend_music(user_emotion, music_data, mode=mode, top_n=count)

    recommended_track_ids = [track['track_id'] for track in res['recommendations']]
    music_instances = Music.objects.filter(id__in=recommended_track_ids)

    daily_rec.music.set(music_instances)
    return res['recommendations']


def get_or_create_movie_recommendation(diary_obj, user_emotion: dict, mode: str, count: int):
    """최초 요청 시 영화 추천을 연산하고, 통합 DailyRecommended 테이블 다대다 관계를 바인딩합니다."""
    daily_rec, created = DailyRecommended.objects.get_or_create(diary=diary_obj)
    movie_data = load_movie_data()

    recommender = MovieEmotionRecommender()
    res = recommender.recommend_movies(user_emotion, movie_data, mode=mode, top_n=count)

    recommended_movie_ids = [movie.get('movie_id') for movie in res['recommendations'] if movie.get('movie_id') is not None]
    movie_instances = Movie.objects.filter(tmdb_id__in=recommended_movie_ids)

    daily_rec.movies.set(movie_instances)
    return res['recommendations']


def get_saved_music_metadata(diary_obj):
    """DailyRecommended 관계를 역참조하여 저장된 음악 인스턴스들의 메타데이터(제목, 이미지, 태그) 목록을 반환합니다."""
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []

    return [
        {
            'track_id': music.id,
            'title': music.title,
            'artist': music.artist if music.artist else '',
            'image_url': music.image_url if music.image_url else '',
            'tags': music.tags if isinstance(music.tags, list) else []
        }
        for music in daily_rec.music.all()
    ]


def get_saved_movie_metadata(diary_obj):
    """DailyRecommended 관계를 역참조하여 저장된 영화 인스턴스들의 메타데이터(제목, 이미지, 태그) 목록을 반환합니다."""
    try:
        daily_rec = DailyRecommended.objects.get(diary=diary_obj)
    except DailyRecommended.DoesNotExist:
        return []

    restored_movies = []
    for movie in daily_rec.movies.all():
        movie_tags = [movie.genre] if movie.genre else []

        restored_movies.append({
            'movie_id': movie.tmdb_id,
            'title': movie.title,
            'director': getattr(movie, 'director', ''),
            'image_url': f"https://image.tmdb.org/t/p/w500{movie.poster_path}" if movie.poster_path else '',
            'tags': movie_tags
        })
    return restored_movies
