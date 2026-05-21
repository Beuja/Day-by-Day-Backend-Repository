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


class MovieEmotionRecommender:
    def recommend_movies(self, user_emotion, movie_data, mode='maintain', top_n=3):
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        
        # 1. 유저 감정 벡터 생성
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        
        # 2. books 앱 스타일의 임계값 및 방향 가중치 변환
        if mode == 'maintain':
            w_vec = u_vec
            radius_limit = 0.4
        elif mode == 'shift':
            max_val = max(u_vec) if max(u_vec) > 0 else 1.0
            w_vec = [v - 0.5 if v == max_val else v for v in u_vec]
            radius_limit = 1.2
        elif mode == 'amplification':
            w_vec = [v * 1.5 for v in u_vec]
            radius_limit = 0.8
        else:
            w_vec = u_vec
            radius_limit = 0.7

        scored_movies = []
        for movie in movie_data:
            tags = movie.get('tags', [])
            b_vec = build_6d_emotion_vector(tags)
            
            # 3. 임계값 범위 필터링 계산 (유클리디안 거리)
            distance = math.sqrt(sum((w_val - b_val) ** 2 for w_val, b_val in zip(w_vec, b_vec)))
            
            if distance <= radius_limit:
                # 4. 코사인 유사도 연산
                dot_product = sum(w_val * b_val for w_val, b_val in zip(w_vec, b_vec))
                mag_w = math.sqrt(sum(w_val ** 2 for w_val in w_vec))
                mag_b = math.sqrt(sum(b_val ** 2 for b_val in b_vec))
                
                cosine_sim = dot_product / (mag_w * mag_b) if mag_w > 0 and mag_b > 0 else 0.0
                
                # 영화 popularity 기반 대중성 점수 계산 (기존 데이터 정규화 수치 준수)
                popularity = float(movie.get('popularity', 0.0))
                popularity_score = min(1.0, popularity / 100000)
                
                final_score = cosine_sim * 0.8 + popularity_score * 0.2
                
                scored_movies.append({
                    'content': movie,
                    'distance': round(distance, 4),
                    'score': round(final_score, 4)
                })

        # 내림차순 정렬 후 슬라이싱 반환
        scored_movies.sort(key=lambda x: x['score'], reverse=True)
        return {
            'mode': mode,
            'radius_limit': radius_limit,
            'recommendations': scored_movies[:top_n]
        }