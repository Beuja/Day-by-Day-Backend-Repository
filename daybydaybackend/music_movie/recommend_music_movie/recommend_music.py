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
        # 💡 안전장치 적용
        if u_vec[0] > 0.5 or u_vec[4] > 0.5:
            target_vec[0] = max(u_vec[0], 0.75)
            target_vec[4] = max(u_vec[4], 0.70)
            target_vec[1] = 0.0
            target_vec[2] = 0.0
            target_vec[3] = 0.0
        else:
            target_vec[0] = 0.85
            target_vec[4] = 0.75
            target_vec[1] = 0.0
            target_vec[2] = 0.0
            target_vec[3] = 0.10
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
        weights[max_emotion_idx] = 3.0
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

class MusicEmotionRecommender:
    def recommend_music(self, user_emotion, music_data, mode='maintain', top_n=3, user=None):
        recent_tags = set()
        liked_music_tags = set()
        disliked_music_tags = set()
        disliked_ids = []

        if user and user.is_authenticated:
            from daybydaybackend.diary.models import DailyRecommended, UserFeedback
            from daybydaybackend.music_movie.models import Music
            from django.contrib.contenttypes.models import ContentType
            from django.utils import timezone
            from datetime import timedelta
            
            recent_recs = DailyRecommended.objects.filter(
                diary__user=user
            ).order_by('-diary__created_at')[:5]
            for rec in recent_recs:
                for ms in rec.musics.all():
                    raw_tags = getattr(ms, 'tags', [])
                    if isinstance(raw_tags, str):
                        raw_tags = raw_tags.replace("'", '"')
                        try: raw_tags = json.loads(raw_tags)
                        except: raw_tags = [raw_tags]
                    elif not isinstance(raw_tags, list): raw_tags = []
                    for t in raw_tags:
                        recent_tags.add(str(t).lower().strip())

            music_type = ContentType.objects.get_for_model(Music)

            liked_ids = UserFeedback.objects.filter(
                user=user, feedback_type='LIKE', content_type=music_type
            ).values_list('object_id', flat=True)
            if liked_ids:
                for m in Music.objects.filter(id__in=liked_ids):
                    rt = m.tags
                    if isinstance(rt, str):
                        rt = rt.replace("'", '"')
                        try: rt = json.loads(rt)
                        except: rt = [rt]
                    elif not isinstance(rt, list): rt = []
                    for t in rt: liked_music_tags.add(str(t).lower().strip())

            # 싫어요 음악 ID 및 기피 태그 수집
            disliked_ids = list(UserFeedback.objects.filter(
                user=user, feedback_type='DISLIKE', content_type=music_type
            ).values_list('object_id', flat=True))

            three_days_ago = timezone.now() - timedelta(days=3)
            recent_disliked_ids = UserFeedback.objects.filter(
                user=user, feedback_type='DISLIKE', content_type=music_type,
                created_at__gte=three_days_ago
            ).values_list('object_id', flat=True)
            if recent_disliked_ids:
                for m in Music.objects.filter(id__in=recent_disliked_ids):
                    rt = m.tags
                    if isinstance(rt, str):
                        rt = rt.replace("'", '"')
                        try: rt = json.loads(rt)
                        except: rt = [rt]
                    elif not isinstance(rt, list): rt = []
                    for t in rt: disliked_music_tags.add(str(t).lower().strip())

        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        
        target_vec = _get_target_emotion_vector(u_vec, mode)
        target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
        w_vec = _get_direction_weights(u_vec, mode)
        
        radius_limit = 0.6 if mode == 'maintain' else (1.2 if mode == 'shift' else 0.8)
        alpha = 0.5
        filtered_and_scored = []
        fallback_list = []

        # [1단계] 순수 감정 후보군 추출
        for music in music_data:
            music_id = str(music.get('track_id') or music.get('id'))
            
            # 🔥 완전 배제 삭제
                
            b_vec = [float(music.get(k, 0.0) or 0.0) for k in ordered_keys]
            raw_tags = music.get('tags', [])
            if isinstance(raw_tags, str):
                raw_tags = raw_tags.replace("'", '"')
                try: raw_tags = json.loads(raw_tags)
                except: raw_tags = [raw_tags]
            elif not isinstance(raw_tags, list): raw_tags = []
                
            if sum(b_vec) < 0.01:
                b_vec = build_6d_emotion_vector(raw_tags)

            pure_distance = math.sqrt(sum((t_val - b) ** 2 for t_val, b in zip(target_vec, b_vec)))
            norm_euclidean = _calculate_euclidean(target_vec, b_vec, w_vec)
            cosine_dist = _calculate_cosine(target_vec, b_vec, target_norm)
            emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)
                
            popularity = float(music.get('listeners', 0) or 0)
            popularity_score = min(1.0, popularity / 50000000.0)
            final_score = (emotion_score * 0.90) + ((1.0 - popularity_score) * 0.10)
            
            current_tags = [str(t).lower().strip() for t in raw_tags]
            if any(t in recent_tags for t in current_tags):
                final_score += 0.25

            music_info = {
                'track_id': int(music_id) if music_id.isdigit() else music_id, 
                'score': round(final_score, 4),
                'pure_distance': pure_distance,
                'tags': raw_tags
            }

            if pure_distance <= radius_limit:
                filtered_and_scored.append(music_info)
            fallback_list.append((music_info, pure_distance))

        pool_size = max(top_n * 3, 10)

        if len(filtered_and_scored) >= top_n:
            filtered_and_scored.sort(key=lambda x: x['score'])
            safe_pool = filtered_and_scored[:pool_size]
            is_fallback = False
        else:
            fallback_list.sort(key=lambda x: x[0]['score'])
            safe_pool = [item[0] for item in fallback_list[:pool_size]]
            is_fallback = True
        
        # =========================================================================
        # [안전장치 및 2단계] 치료 임계치 검증 & 취향 정렬
        # =========================================================================
        if user and user.is_authenticated and len(safe_pool) > 0:
            therapeutic_threshold = radius_limit * 0.5
            has_effective_preferred_music = False

            for item in safe_pool:
                tags = item.get('tags', [])
                pure_dist = item.get('pure_distance', 9.9)
                tag_list = [str(g).lower().strip() for g in tags]
                
                if any(g in liked_music_tags for g in tag_list):
                    if pure_dist <= therapeutic_threshold:
                        has_effective_preferred_music = True
                        break

            # 💡 [books 방식 통일] 완전 배제 대신 패널티 부여!
            def get_preference_rank(item):
                tags = item.get('tags', [])
                rank_modifier = 0
                tag_list = [str(g).lower().strip() for g in tags]
                
                if any(g in liked_music_tags for g in tag_list) and has_effective_preferred_music:
                    rank_modifier -= 10
                if any(g in disliked_music_tags for g in tag_list):
                    rank_modifier += 10
                
                # 싫어요 누른 특정 음악에 강력한 패널티 부여 (+15점)
                if str(item.get('track_id')) in map(str, disliked_ids):
                    rank_modifier += 15

                return rank_modifier

            safe_pool.sort(key=get_preference_rank)

        selected_musics = safe_pool[:top_n]
        music_ids = [m['track_id'] for m in selected_musics]
        from daybydaybackend.music_movie.models import Music
        music_map = {m.id: m for m in Music.objects.filter(id__in=music_ids)}
        
        recommended_musics = []
        for m in selected_musics:
            mid = m['track_id']
            if mid in music_map:
                obj = music_map[mid]
                obj.score = m['score']
                recommended_musics.append(obj)
                
        return {
            "recommendations": recommended_musics, 
            "is_fallback": is_fallback
        }