import os
import json
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'emotion_tags.json')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    TAG_EMOTION_MAP = json.load(f)

def build_6d_emotion_vector(tags):
    ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
    total_vector = {key: 0.0 for key in ordered_keys}
    matched_count = 0
    for tag in tags:
        tag = str(tag).lower().strip()
        if tag in TAG_EMOTION_MAP:
            matched_count += 1
            tag_vec = TAG_EMOTION_MAP[tag]
            for key in ordered_keys:
                total_vector[key] += tag_vec.get(key, 0.0)
    if matched_count == 0:
        return [0.0] * 6
    return [round(total_vector[key] / matched_count, 4) for key in ordered_keys]

def _get_target_emotion_vector(u_vec, mode):
    target_vec = list(u_vec)
    if mode == 'shift':
        target_vec[0] = u_vec[1]; target_vec[1] = u_vec[0] 
        target_vec[2] = u_vec[4]; target_vec[4] = u_vec[2] 
        target_vec[3] = u_vec[5]; target_vec[5] = u_vec[3] 
        if sum(target_vec) < 0.1:
            target_vec[0] = 0.8; target_vec[4] = 0.5
    elif mode == 'amplification':
        max_val = max(target_vec)
        if max_val > 0.01:
            max_idx = target_vec.index(max_val)
            target_vec[max_idx] = 1.0 
            for i in range(len(target_vec)):
                if i != max_idx: target_vec[i] = 0.0
        else:
            target_vec[0] = 1.0
    return target_vec

def _get_direction_weights(u_vec, mode):
    weights = [1.0] * 6
    if mode == 'maintain': 
        return weights
    elif mode == 'shift':
        target = _get_target_emotion_vector(u_vec, mode)
        weights = [2.0 if t > 0.5 else 1.0 for t in target]
    elif mode == 'amplification':
        max_emotion_idx = u_vec.index(max(u_vec)) if max(u_vec) > 0.01 else 0
        weights = [0.1] * 6
        weights[max_emotion_idx] = 3.0 # 💡 감정 증폭 가중치 
    return weights

def _calculate_euclidean(u_vec, b_vec, w_vec):
    euclidean_dist = math.sqrt(sum(w * ((u - b) ** 2) for u, b, w in zip(u_vec, b_vec, w_vec)))
    max_euclidean = math.sqrt(sum(w_vec)) 
    if max_euclidean == 0: return 0.0
    return euclidean_dist / max_euclidean

def _calculate_cosine(u_vec, b_vec, u_norm):
    b_norm = math.sqrt(sum(b ** 2 for b in b_vec)) or 1e-9
    dot_product = sum(u * b for u, b in zip(u_vec, b_vec))
    return 1.0 - (dot_product / (u_norm * b_norm))

class MovieEmotionRecommender:
    def recommend_movies(self, user_emotion, movie_data, mode='maintain', top_n=3):
        from daybydaybackend.music_movie.models import Movie
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        
        target_vec = _get_target_emotion_vector(u_vec, mode)
        target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
        w_vec = _get_direction_weights(u_vec, mode)
        
        radius_limit = 0.6 if mode == 'maintain' else (1.2 if mode == 'shift' else 0.8)
        alpha = 0.5
        filtered_and_scored = []
        fallback_list = []

        for movie in movie_data:
            b_vec = [float(movie.get(k, 0.0) or 0.0) for k in ordered_keys]
            if sum(b_vec) < 0.01:
                raw_tags = movie.get('tags', [])
                if isinstance(raw_tags, str):
                    raw_tags = raw_tags.replace("'", '"')
                    try: raw_tags = json.loads(raw_tags)
                    except: raw_tags = [raw_tags]
                elif not isinstance(raw_tags, list): raw_tags = []
                b_vec = build_6d_emotion_vector(raw_tags)

            pure_distance = math.sqrt(sum((t_val - b) ** 2 for t_val, b in zip(target_vec, b_vec)))
            norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
            cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
            emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
            popularity = float(movie.get('popularity', 0.0) or 0.0)
            popularity_score = min(1.0, popularity / 500.0)
            
            # 💡 감정 점수 반영률 90%, 대중성 10%
            final_score = (emotion_score * 0.90) + ((1.0 - popularity_score) * 0.10)
            movie_info = {'movie_id': movie.get('movie_id'), 'score': round(final_score, 4)}

            if pure_distance <= radius_limit:
                filtered_and_scored.append(movie_info)
            
            fallback_list.append((movie_info, pure_distance))

        if len(filtered_and_scored) >= top_n:
            filtered_and_scored.sort(key=lambda x: x['score'])
            selected_movies = filtered_and_scored[:top_n]
            is_fallback = False
        else:
            fallback_list.sort(key=lambda x: x[0]['score'])
            selected_movies = [item[0] for item in fallback_list[:top_n]]
            is_fallback = True
        
    
        movie_ids = [m['movie_id'] for m in selected_movies]
        movie_map = {m.tmdb_id: m for m in Movie.objects.filter(tmdb_id__in=movie_ids)}
        
        recommended_movies = []
        for m in selected_movies:
            mid = m['movie_id']
            if mid in movie_map:
                obj = movie_map[mid]
                obj.score = m['score']
                recommended_movies.append(obj)
                
        return {
            "recommendations": recommended_movies, 
            "is_fallback": is_fallback
        }
       