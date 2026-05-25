# music_movie/recommend_music_movie/recommend_movie.py
import os
import json
import math

# emotion_tags.json 파일 경로 설정 및 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'emotion_tags.json')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    TAG_EMOTION_MAP = json.load(f)

def build_6d_emotion_vector(tags):
    """영화 메타태그 가중치를 종합하여 6차원 감정 벡터 리스트를 빌드합니다."""
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

def _get_direction_weights(u_vec, mode):
    # 모드별 가중치 벡터 w 생성 함수
    weights = [1.0] * 6
    
    if mode == 'maintain':
        return weights
    
    elif mode == 'shift':
        # sadness, anger, fear 패널티, joy, trust 인센티브, surprise 유지
        weights[0] = 0.5    # joy
        weights[1] = 2.0    # sadness
        weights[2] = 2.0    # anger
        weights[3] = 2.0    # fear
        weights[4] = 0.5    # trust
        weights[5] = 1.0    # surprise
        
    elif mode == 'amplification':
        max_val = max(u_vec)
        max_emotion_idx = u_vec.index(max_val)
        weights[max_emotion_idx] = 0.2
        
    return weights

def _calculate_euclidean(u_vec, b_vec, w_vec):
    # 가중 유클리드 거리 계산 및 정규화 (0~1 사이)
    euclidean_dist = math.sqrt(sum(w * ((u - b) ** 2) for u, b, w in zip(u_vec, b_vec, w_vec)))
    sum_w = sum(w_vec)
    max_euclidean = math.sqrt(sum(w * sum_w for w in w_vec))
    
    if max_euclidean == 0:
        return 0.0
    return euclidean_dist / max_euclidean

def _calculate_cosine(u_vec, b_vec, u_norm):
    # 코사인 유사도 계산
    b_norm = math.sqrt(sum(b ** 2 for b in b_vec))

    if b_norm == 0:
        b_norm = 1e-9

    dot_product = sum(u * b for u, b in zip(u_vec, b_vec))
    cosine_sim = dot_product / (u_norm * b_norm)
    return 1.0 - cosine_sim


class MovieEmotionRecommender:
    def recommend_movies(self, user_emotion, movie_data, mode='maintain', top_n=3):
        # 계산을 위해 리스트 형태로 변경
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        u_norm = math.sqrt(sum(u ** 2 for u in u_vec))
        if u_norm == 0:
            u_norm = 1e-9
            
        w_vec = _get_direction_weights(u_vec, mode)
        
        # 감정 범위 임계값
        if mode == 'maintain':
            radius_limit = 0.4
        elif mode == 'shift':
            radius_limit = 1.2
        elif mode == 'amplification':
            radius_limit = 0.8
        else:
            radius_limit = 0.7
            
        # 코사인 유사도&유클리드 거리 결합 가중치 (1에 가까울 수록 유클리드 거리 중시)
        alpha = 0.5
        filtered_and_scored = []
        
        for movie in movie_data:
            orig_tags = movie.get('tags', [])
            b_vec = [
                float(movie.get('joy', 0.0) if movie.get('joy') is not None else 0.0),
                float(movie.get('sadness', 0.0) if movie.get('sadness') is not None else 0.0),
                float(movie.get('anger', 0.0) if movie.get('anger') is not None else 0.0),
                float(movie.get('fear', 0.0) if movie.get('fear') is not None else 0.0),
                float(movie.get('trust', 0.0) if movie.get('trust') is not None else 0.0),
                float(movie.get('surprise', 0.0) if movie.get('surprise') is not None else 0.0),
            ]
            
            # 순수 유클리드 거리
            pure_distance = math.sqrt(sum((u - b) ** 2 for u, b in zip(u_vec, b_vec)))
            
            if pure_distance <= radius_limit:
                norm_euclidean = _calculate_euclidean(u_vec, b_vec, w_vec)
                cosine_dist = _calculate_cosine(u_vec, b_vec, u_norm)
                
                # 최종 점수
                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
                # 영화 popularity 기반 대중성 점수 반영
                popularity = float(movie.get('popularity', 0.0))
                popularity_score = min(1.0, popularity / 100000)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)
                
                filtered_and_scored.append({
                    'movie_id': movie.get('movie_id'),
                    'title': movie.get('title'),
                    'director': movie.get('director'),
                    'image_url': movie.get('image_url', ''),
                    'tags': orig_tags,
                    'score': round(final_score, 4)
                })

        filtered_and_scored.sort(key=lambda x: x['score'])
        return filtered_and_scored[:top_n]