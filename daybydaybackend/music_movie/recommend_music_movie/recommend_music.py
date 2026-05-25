# music_movie/recommend_music_movie/recommend_music.py
import os
import json
import math

# emotion_tags.json 파일 경로 설정 및 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'emotion_tags.json')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    TAG_EMOTION_MAP = json.load(f)

def build_6d_emotion_vector(tags):
    """콘텐츠 태그 가중치를 종합하여 6차원 감정 벡터를 리스트 형태로 빌드합니다."""
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
    """추천 모드에 따라 추천의 기준이 될 목표 감정 벡터를 생성합니다."""
    target_vec = list(u_vec)  # 안전한 연산을 위해 리스트 복사
    
    # 인덱스: 0=joy, 1=sadness, 2=anger, 3=fear, 4=trust, 5=surprise
    if mode == 'shift':
        # 부정적 감정은 완전히 지우지 않고 20% 수준으로 남겨 자연스러운 공감 유도
        target_vec[1] *= 0.2  # sadness
        target_vec[2] *= 0.2  # anger
        target_vec[3] *= 0.2  # fear
        
        # 긍정적 감정 증대 (최대 1.0 제한)
        target_vec[0] = min(target_vec[0] + 0.5, 1.0)  # joy
        target_vec[4] = min(target_vec[4] + 0.4, 1.0)  # trust
        
    elif mode == 'amplification':
        # 가장 지배적인 감정을 더욱 증폭
        max_val = max(target_vec)
        if max_val > 0:
            max_idx = target_vec.index(max_val)
            target_vec[max_idx] = min(target_vec[max_idx] * 1.5, 1.0)
        
    return target_vec

def _get_direction_weights(u_vec, mode):
    # 모드별 가중치 벡터 w 생성 함수
    weights = [1.0] * 6 # np.ones(6) 대신 리스트 기본값 초기화
    
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


class MusicEmotionRecommender:
    def recommend_music(self, user_emotion, music_data, mode='maintain', top_n=3):
        from daybydaybackend.music_movie.models import Music  # 순환 참조 방지
        
        # 계산을 위해 리스트 형태로 변경
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        
        # 유저 감정에서 도서 팀원의 알고리즘 조율을 마친 타겟 감정 벡터 중심점 획득
        target_vec = _get_target_emotion_vector(u_vec, mode)
        target_norm = math.sqrt(sum(t ** 2 for t in target_vec))
        if target_norm == 0:
            target_norm = 1e-9
            
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
            
        alpha = 0.5
        filtered_and_scored = []
        
        for track in music_data:
            orig_tags = track.get('tags', [])
            b_vec = [
                float(track.get('joy', 0.0) if track.get('joy') is not None else 0.0),
                float(track.get('sadness', 0.0) if track.get('sadness') is not None else 0.0),
                float(track.get('anger', 0.0) if track.get('anger') is not None else 0.0),
                float(track.get('fear', 0.0) if track.get('fear') is not None else 0.0),
                float(track.get('trust', 0.0) if track.get('trust') is not None else 0.0),
                float(track.get('surprise', 0.0) if track.get('surprise') is not None else 0.0),
            ]
            
            # 순수 유클리드 거리 판단의 기준점을 u_vec 대신 모드별 target_vec으로 수정
            pure_distance = math.sqrt(sum((t - b) ** 2 for t, b in zip(target_vec, b_vec)))
            
            if pure_distance <= radius_limit:
                norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
                cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
                
                # 최종 점수
                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
                # 대중성 가중치 결합 연산부 (listeners 기반 인센티브)
                popularity = int(track.get('listeners', 0))
                popularity_score = min(1.0, popularity / 1000000)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)
                
                filtered_and_scored.append({
                    'track_id': track.get('track_id'),
                    'score': round(final_score, 4)
                })
                
        # 거리가 가까운 순으로 오름차순 정렬 처리
        filtered_and_scored.sort(key=lambda x: x['score'])
        
        # [도서 로직 반영 Fallback] 반경 내에 음악이 하나도 걸리지 않을 경우 강제 예외 복구 분기
        if not filtered_and_scored:
            fallback_list = []
            for track in music_data:
                b_vec = [
                    float(track.get('joy', 0.0) if track.get('joy') is not None else 0.0),
                    float(track.get('sadness', 0.0) if track.get('sadness') is not None else 0.0),
                    float(track.get('anger', 0.0) if track.get('anger') is not None else 0.0),
                    float(track.get('fear', 0.0) if track.get('fear') is not None else 0.0),
                    float(track.get('trust', 0.0) if track.get('trust') is not None else 0.0),
                    float(track.get('surprise', 0.0) if track.get('surprise') is not None else 0.0),
                ]
                pure_distance = math.sqrt(sum((target_vec - b) ** 2 for target_vec, b in zip(target_vec, b_vec)))
                norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
                cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
                popularity = int(track.get('listeners', 0))
                popularity_score = min(1.0, popularity / 1000000)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)
                
                fallback_list.append(({
                    'track_id': track.get('track_id'),
                    'score': round(final_score, 4)
                }, pure_distance))
            
            fallback_list.sort(key=lambda x: x[1])
            selected_tracks = fallback_list[:top_n]
            track_ids = [item[0]['track_id'] for item in selected_tracks]
            
            music_map = {m.id: m for m in Music.objects.filter(id__in=track_ids)}
            recommended_tracks = []
            for item in selected_tracks:
                tid = item[0]['track_id']
                if tid in music_map:
                    recommended_tracks.append(music_map[tid])
            return {"recommendations": recommended_tracks}
        
        # 정상 필터링 매칭 시 처리 영역
        selected_tracks = filtered_and_scored[:top_n]
        track_ids = [t['track_id'] for t in selected_tracks]
        music_map = {m.id: m for m in Music.objects.filter(id__in=track_ids)}
        
        recommended_tracks = []
        for t in selected_tracks:
            tid = t['track_id']
            if tid in music_map:
                recommended_tracks.append(music_map[tid])
                
        return {"recommendations": recommended_tracks}