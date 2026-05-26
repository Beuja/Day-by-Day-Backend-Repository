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
        # 정반대 감정으로 기분 전환 스위칭(Cross-Inversion)
        target_vec[0] = u_vec[1] # joy <- sadness
        target_vec[1] = u_vec[0] # sadness <- joy
        target_vec[2] = u_vec[4] # anger <- trust
        target_vec[4] = u_vec[2] # trust <- anger
        target_vec[3] = u_vec[5] # fear <- surprise
        target_vec[5] = u_vec[3] # surprise <- fear
        
        # 감정이 거의 없었다면 무기력함을 깨도록 긍정 에너지 주입
        if sum(target_vec) < 0.1:
            target_vec[0] = 0.8
            target_vec[4] = 0.5
            
    elif mode == 'amplification':
        max_val = max(target_vec)
        if max_val > 0:
            max_idx = target_vec.index(max_val)
            target_vec[max_idx] = min(target_vec[max_idx] * 1.5, 1.0)
            for i in range(len(target_vec)):
                if i != max_idx:
                    target_vec[i] *= 0.5
    return target_vec

def _get_direction_weights(u_vec, mode):
    weights = [1.0] * 6
    
    if mode == 'maintain': 
        return weights
        
    elif mode == 'shift':
        target = _get_target_emotion_vector(u_vec, mode)
        weights = [2.0 if t > 0.5 else 1.0 for t in target]
        
    elif mode == 'amplification':
        max_emotion_idx = u_vec.index(max(u_vec))
        weights[max_emotion_idx] = 3.0 
    return weights

def _calculate_euclidean(u_vec, b_vec, w_vec):
    euclidean_dist = math.sqrt(sum(w * ((u - b) ** 2) for u, b, w in zip(u_vec, b_vec, w_vec)))
    max_euclidean = math.sqrt(sum(w_vec)) 
    if max_euclidean == 0:
        return 0.0
    return euclidean_dist / max_euclidean

def _calculate_cosine(u_vec, b_vec, u_norm):
    b_norm = math.sqrt(sum(b ** 2 for b in b_vec)) or 1e-9
    dot_product = sum(u * b for u, b in zip(u_vec, b_vec))
    return 1.0 - (dot_product / (u_norm * b_norm))

class MusicEmotionRecommender:
    def recommend_music(self, user_emotion, music_data, mode='maintain', top_n=3):
        from daybydaybackend.music_movie.models import Music
        
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        
        target_vec = _get_target_emotion_vector(u_vec, mode)
        target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
        w_vec = _get_direction_weights(u_vec, mode)
        
        radius_limit = 0.5 if mode == 'maintain' else (1.2 if mode == 'shift' else 0.8)
        alpha = 0.5
        filtered_and_scored = []
        
        for track in music_data:
            b_vec = [float(track.get(k, 0.0) or 0.0) for k in ordered_keys]
            pure_distance = math.sqrt(sum((t_val - b) ** 2 for t_val, b in zip(target_vec, b_vec)))
            
            if pure_distance <= radius_limit:
                norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
                cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
                popularity = int(track.get('listeners', 0))
                popularity_score = min(1.0, popularity / 1000000)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)
                
                filtered_and_scored.append({'track_id': track.get('track_id'), 'score': round(final_score, 4)})
                
        filtered_and_scored.sort(key=lambda x: x['score'])
        
        if not filtered_and_scored:
            fallback_list = []
            for track in music_data:
                b_vec = [float(track.get(k, 0.0) or 0.0) for k in ordered_keys]
                pure_distance = math.sqrt(sum((t_val - b) ** 2 for t_val, b in zip(target_vec, b_vec)))
                norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
                cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
                popularity = int(track.get('listeners', 0))
                popularity_score = min(1.0, popularity / 1000000)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)
                
                fallback_list.append(({'track_id': track.get('track_id'), 'score': round(final_score, 4)}, pure_distance))
            
            fallback_list.sort(key=lambda x: x[1])
            selected_tracks = fallback_list[:top_n]
            track_ids = [item[0]['track_id'] for item in selected_tracks]
            
            music_map = {m.id: m for m in Music.objects.filter(id__in=track_ids)}
            recommended_tracks = []
            for item in selected_tracks:
                tid = item[0]['track_id']
                if tid in music_map:
                    obj = music_map[tid]
                    obj.score = item[0]['score']
                    recommended_tracks.append(obj)
            return {"recommendations": recommended_tracks}
        
        selected_tracks = filtered_and_scored[:top_n]
        track_ids = [t['track_id'] for t in selected_tracks]
        music_map = {m.id: m for m in Music.objects.filter(id__in=track_ids)}
        
        recommended_tracks = []
        for t in selected_tracks:
            tid = t['track_id']
            if tid in music_map:
                obj = music_map[tid]
                obj.score = t['score']
                recommended_tracks.append(obj)
                
        return {"recommendations": recommended_tracks}