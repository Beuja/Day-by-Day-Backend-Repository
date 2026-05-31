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
        weights[max_emotion_idx] = 6.0 # 💡 감정 증폭 가중치 상승
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
        return self.recommend_musics(user_emotion, music_data, mode=mode, top_n=top_n, user=user)

    def recommend_musics(self, user_emotion, music_data, mode='maintain', top_n=3, user=None):
        recent_tags = set()
        if user and user.is_authenticated:
            from daybydaybackend.diary.models import DailyRecommended
            recent_recs = DailyRecommended.objects.filter(
                diary__user=user
            ).order_by('-diary__created_at')[:5]
            for rec in recent_recs:
                for m in rec.musics.all():
                    for tag in getattr(m, 'tags', []):
                        recent_tags.add(str(tag).lower().strip())
        from daybydaybackend.music_movie.models import Music
        ordered_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ordered_keys]
        target_vec = _get_target_emotion_vector(u_vec, mode)
        target_norm = math.sqrt(sum(t ** 2 for t in target_vec)) or 1e-9
        w_vec = _get_direction_weights(u_vec, mode)
        
        radius_limit = 0.6 if mode == 'maintain' else (1.2 if mode == 'shift' else 0.8)
        alpha = 0.5
        filtered_and_scored = []
        fallback_list = []

        for track in music_data:
            b_vec = [float(track.get(k, 0.0) or 0.0) for k in ordered_keys]
            if sum(b_vec) < 0.01:
                raw_tags = track.get('tags', [])
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
                
            popularity = float(track.get('listeners', 0) or 0)
            popularity_score = min(1.0, popularity / 50000000.0)
            # 💡 감정 점수 반영률 90%, 대중성 10% 로 조정 (동점 방지)
            final_score = (emotion_score * 0.9) + ((1.0 - popularity_score) * 0.1)
            
            # [다양성 패치] 최근 추천받았던 태그들과 중복되는 감정 태그가 있다면 패널티 가산
            track_tags = track.get('tags', [])
            if isinstance(track_tags, str):
                track_tags = track_tags.replace("'", '"')
                try: track_tags = json.loads(track_tags)
                except: track_tags = [track_tags]
            
            overlap = sum(1 for t in track_tags if str(t).lower().strip() in recent_tags)
            if overlap > 0:
                final_score += 0.2

            track_info = {
                'track_id': track.get('track_id'), 
                'score': round(final_score, 4),
                'pure_distance': pure_distance,
                'tags': track_tags
            }
                
            if pure_distance <= radius_limit:
                filtered_and_scored.append(track_info)
        
            fallback_list.append((track_info, pure_distance))

        # [1단계] 객관적인 감정 치료 우선으로 안전 후보군 선별
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
        # [안전장치 및 2단계] 치료 임계치 검증 & 안전 후보군 내 취향 재정렬
        # =========================================================================
        if user and user.is_authenticated and len(safe_pool) > 0:
            from daybydaybackend.diary.models import UserFeedback
            from django.contrib.contenttypes.models import ContentType
            from django.utils import timezone
            from datetime import timedelta

            liked_music_tags = set()
            disliked_music_tags = set()

            music_type = ContentType.objects.get_for_model(Music)
            
            # 좋아요 음악의 태그 수집
            liked_ids = UserFeedback.objects.filter(
                user=user, feedback_type='LIKE', content_type=music_type
            ).values_list('object_id', flat=True)
            if liked_ids:
                for m in Music.objects.filter(id__in=liked_ids):
                    for tag in getattr(m, 'tags', []):
                        liked_music_tags.add(str(tag).lower().strip())

            # 최근 3일 싫어요 음악의 태그 수집
            three_days_ago = timezone.now() - timedelta(days=3)
            disliked_ids = UserFeedback.objects.filter(
                user=user, feedback_type='DISLIKE', content_type=music_type,
                created_at__gte=three_days_ago
            ).values_list('object_id', flat=True)
            if disliked_ids:
                for m in Music.objects.filter(id__in=disliked_ids):
                    for tag in getattr(m, 'tags', []):
                        disliked_music_tags.add(str(tag).lower().strip())

            # 치료 마지노선 임계값 = radius_limit * 0.5
            therapeutic_threshold = radius_limit * 0.5
            has_effective_preferred_music = False

            for item in safe_pool:
                t_tags = item.get('tags', [])
                pure_dist = item.get('pure_distance', 9.9)
                t_tags_clean = [str(t).lower().strip() for t in t_tags]
                if any(t in liked_music_tags for t in t_tags_clean):
                    if pure_dist <= therapeutic_threshold:
                        has_effective_preferred_music = True
                        break

            # 순위 재정렬 함수 정의
            def get_preference_rank(item):
                t_tags = item.get('tags', [])
                t_tags_clean = [str(t).lower().strip() for t in t_tags]
                rank_modifier = 0
                if any(t in liked_music_tags for t in t_tags_clean) and has_effective_preferred_music:
                    rank_modifier -= 10
                if any(t in disliked_music_tags for t in t_tags_clean):
                    rank_modifier += 10
                return rank_modifier

            # Python의 stable sort 특성을 이용해 순서 교정
            safe_pool.sort(key=get_preference_rank)

        selected_tracks = safe_pool[:top_n]
        track_ids = [t['track_id'] for t in selected_tracks]
        music_map = {m.id: m for m in Music.objects.filter(id__in=track_ids)}
        
        recommended_tracks = []
        for t in selected_tracks:
            tid = t['track_id']
            if tid in music_map:
                obj = music_map[tid]
                obj.score = t['score']
                recommended_tracks.append(obj)

        return {
            "recommendations": recommended_tracks,
            "is_fallback": is_fallback
        }