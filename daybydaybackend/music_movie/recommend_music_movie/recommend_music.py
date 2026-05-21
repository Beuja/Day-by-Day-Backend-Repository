# music_movie/recommend_music_movie/recommend_music.py
import os
import json
import math

# emotion_tags.json 파일 경로 설정 및 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'emotion_tags.json')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    TAG_EMOTION_MAP = json.load(f)

def _get_direction_weights(u_vec, mode):
    """books 앱의 가중치 방향 벡터 생성 로직을 따릅니다."""
    if mode == 'maintain':
        return u_vec
    elif mode == 'shift':
        # 감정을 전환하는 방향 (가장 높은 감정을 낮추고 나머지를 보완하는 등 기획된 공식 적용)
        max_idx = u_vec.argmax() if u_vec.max() > 0 else 0
        w = u_vec.copy()
        w[max_idx] = max(0.0, w[max_idx] - 0.5)
        return w
    elif mode == 'amplification':
        return u_vec * 1.5
    return u_vec

def build_6d_emotion_vector(tags):
    """콘텐츠 태그 가중치를 종합하여 6차원 감정 벡터를 리스트(배열) 형태로 빌드합니다."""
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

class MusicEmotionRecommender:
    def recommend_music(self, user_emotion, music_data, mode='maintain', top_n=3):
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        
        # 1. 유저 감정 벡터 생성
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        
        # 2. mode 별 방향 가중치 벡터 계산
        # 정밀 연산을 위해 임시 매핑 (NumPy 의존성 최소화를 위해 원시 math/list 연산 구현)
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

        scored_tracks = []
        for track in music_data:
            tags = track.get('tags', [])
            # 콘텐츠의 6차원 감정 벡터 추출
            b_vec = build_6d_emotion_vector(tags)
            
            # 3. 임계값(radius_limit) 필터링을 위한 유클리디안 거리 계산
            distance = math.sqrt(sum((w_val - b_val) ** 2 for w_val, b_val in zip(w_vec, b_vec)))
            
            if distance <= radius_limit:
                # 4. 코사인 유사도 점수 계산
                dot_product = sum(w_val * b_val for w_val, b_val in zip(w_vec, b_vec))
                mag_w = math.sqrt(sum(w_val ** 2 for w_val in w_vec))
                mag_b = math.sqrt(sum(b_val ** 2 for b_val in b_vec))
                
                cosine_sim = dot_product / (mag_w * mag_b) if mag_w > 0 and mag_b > 0 else 0.0
                
                # 대중성 점수 반영 (listeners 수치 활용)
                popularity = int(track.get('listeners', 0))
                popularity_score = min(1.0, popularity / 1000000)
                
                # 최종 추천 결합 스코어 (감정 유사도 80% + 대중성 20%)
                final_score = cosine_sim * 0.8 + popularity_score * 0.2
                
                scored_tracks.append({
                    'content': track,
                    'distance': round(distance, 4),
                    'score': round(final_score, 4)
                })

        # Score 기준 내림차순 정렬
        scored_tracks.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'mode': mode,
            'radius_limit': radius_limit,
            'recommendations': scored_tracks[:top_n]
        }