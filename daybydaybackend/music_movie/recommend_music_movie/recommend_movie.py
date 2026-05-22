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
    """books 앱의 모드별 가중치 벡터 w 생성 로직과 완전히 일치합니다."""
    weights = [1.0] * 6
    
    if mode == 'maintain':
        return weights
    
    elif mode == 'shift':
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
    """가중 유클리드 거리 계산 및 정규화"""
    euclidean_dist = math.sqrt(sum(w * ((u - b) ** 2) for u, b, w in zip(u_vec, b_vec, w_vec)))
    sum_w = sum(w_vec)
    max_euclidean = math.sqrt(sum(w * sum_w for w in w_vec))
    
    if max_euclidean == 0:
        return 0.0
    return euclidean_dist / max_euclidean

def _calculate_cosine(u_vec, b_vec, u_norm):
    """코사인 거리 계산 (1.0 - cosine_sim)"""
    b_norm = math.sqrt(sum(b ** 2 for b in b_vec))
    if b_norm == 0:
        b_norm = 1e-9
        
    dot_product = sum(u * b for u, b in zip(u_vec, b_vec))
    cosine_sim = dot_product / (u_norm * b_norm)
    return 1.0 - cosine_sim


class MovieEmotionRecommender:
    def recommend_movies(self, user_emotion, movie_data, mode='maintain', top_n=3):
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        
        # 1. 유저 감정 벡터 및 노름 생성
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        u_norm = math.sqrt(sum(u ** 2 for u in u_vec))
        if u_norm == 0:
            u_norm = 1e-9
            
        # 2. 가중치 벡터 w 생성 및 임계값 설정
        w_vec = _get_direction_weights(u_vec, mode)
        
        if mode == 'maintain':
            radius_limit = 0.4
        elif mode == 'shift':
            radius_limit = 1.2
        elif mode == 'amplification':
            radius_limit = 0.8
        else:
            radius_limit = 0.7
            
        alpha = 0.5
        filtered_and_scored = []
        
        # 3. 데이터베이스 순회 및 가중 점수 계산
        for movie in movie_data:
            tags = movie.get('tags', [])
            b_vec = build_6d_emotion_vector(tags)
            
            # 순수 유클리드 거리 계산
            pure_distance = math.sqrt(sum((u - b) ** 2 for u, b in zip(u_vec, b_vec)))
            
            if pure_distance <= radius_limit:
                norm_euclidean = _calculate_euclidean(u_vec, b_vec, w_vec)
                cosine_dist = _calculate_cosine(u_vec, b_vec, u_norm)
                
                # 최종 감정 거리 점수 (낮을수록 좋음)
                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
                # 영화 popularity 기반 대중성 점수 반영
                # 인기도가 높을수록 감정 거리를 좁혀 우선순위로 올라오도록 계산
                popularity = float(movie.get('popularity', 0.0))
                popularity_score = min(1.0, popularity / 100000)
                
                # 최종 결합 스코어 (감정 거리 점수 80% + 대중성 인센티브 20%)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)
                
                filtered_and_scored.append({
                    'content': movie,
                    'score': round(final_score, 4)
                })

        # 거리가 가까운(Score가 낮은) 순서대로 오름차순 정렬 후 슬라이싱
        filtered_and_scored.sort(key=lambda x: x['score'])
        
        return {
            'mode': mode,
            'radius_limit': radius_limit,
            'recommendations': [item['content'] for item in filtered_and_scored[:top_n]]
        }