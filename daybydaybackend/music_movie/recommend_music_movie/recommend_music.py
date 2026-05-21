# music_movie/recommend_music_movie/recommend_music.py
import os
import json
import math

# emotion_tags.json 파일 경로 설정 및 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'emotion_tags.json')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    TAG_EMOTION_MAP = json.load(f)

def extract_user_emotion(user_emotion):
    if isinstance(user_emotion, dict):
        return (
            float(user_emotion.get('valence', 0.0)),
            float(user_emotion.get('arousal', 0.0)),
        )
    if isinstance(user_emotion, (list, tuple)) and len(user_emotion) >= 2:
        return (float(user_emotion[0]), float(user_emotion[1]))
    raise ValueError(
        'user_emotion must be a dict or tuple/list containing (valence, arousal)'
    )


def convert_tag_vector_to_russell(tag_vector):
    valence = (
        tag_vector.get('joy', 0) * 1.0 +
        tag_vector.get('romance', 0) * 0.7 +
        tag_vector.get('calmness', 0) * 0.4 +
        tag_vector.get('sadness', 0) * -1.0 +
        tag_vector.get('anger', 0) * -0.8 +
        tag_vector.get('fear', 0) * -0.7 +
        tag_vector.get('darkness', 0) * -0.6
    )
    arousal = (
        tag_vector.get('energy', 0) * 1.0 +
        tag_vector.get('anger', 0) * 0.7 +
        tag_vector.get('fear', 0) * 0.6 +
        tag_vector.get('dreaminess', 0) * -0.2 +
        tag_vector.get('calmness', 0) * -0.7
    )
    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))
    return valence, arousal


def build_russell_emotion(tags):
    total_valence = 0.0
    total_arousal = 0.0
    matched_count = 0

    for tag in tags:
        tag = str(tag).lower().strip()
        if tag in TAG_EMOTION_MAP:
            matched_count += 1
            tag_valence, tag_arousal = convert_tag_vector_to_russell(TAG_EMOTION_MAP[tag])
            total_valence += tag_valence
            total_arousal += tag_arousal

    if matched_count == 0:
        return {'valence': 0.0, 'arousal': 0.0}

    valence = max(-1.0, min(1.0, total_valence / matched_count))
    arousal = max(-1.0, min(1.0, total_arousal / matched_count))
    return {'valence': round(valence, 3), 'arousal': round(arousal, 3)}


class EmotionStrategy:
    @staticmethod
    def get_strategy(valence, arousal):
        if valence > 0 and arousal > 0:
            return {
                'strategy': 'amplify',
                'target_valence': min(1.0, valence + 0.2),
                'target_arousal': min(1.0, arousal + 0.1),
                'description': '긍정적 고양감 증폭',
            }
        elif valence > 0 and arousal <= 0:
            return {
                'strategy': 'stabilize',
                'target_valence': valence,
                'target_arousal': arousal,
                'description': '평온한 상태 유지',
            }
        elif valence <= 0 and arousal > 0:
            return {
                'strategy': 'release',
                'target_valence': min(0.3, valence + 0.5),
                'target_arousal': max(-0.3, arousal - 0.4),
                'description': '긴장과 스트레스 해소',
            }
        else:
            return {
                'strategy': 'energize',
                'target_valence': min(0.4, valence + 0.6),
                'target_arousal': min(0.3, arousal + 0.5),
                'description': '우울 상태 활력 제공',
            }


class SimilarityCalculator:
    @staticmethod
    def cosine_similarity(v1, v2):
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        magnitude1 = math.sqrt(v1[0]**2 + v1[1]**2)
        magnitude2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def euclidean_distance(v1, v2):
        return math.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)

    @staticmethod
    def combined_score(current, target, popularity=0, cosine_weight=0.6):
        cos_sim = SimilarityCalculator.cosine_similarity(current, target)
        distance = SimilarityCalculator.euclidean_distance(current, target)
        distance_score = 1 / (1 + distance)
        emotion_score = cosine_weight * cos_sim + (1 - cosine_weight) * distance_score
        
        # 음악 listeners 기반 대중성 점수 계산
        popularity_score = min(1.0, popularity / 1000000)
        final_score = emotion_score * 0.8 + popularity_score * 0.2
        return round(final_score, 4)


def get_target_emotion(valence, arousal, mode):
    if mode == 'maintain':
        return (valence, arousal)
    elif mode == 'shift':
        return (-0.5 if valence >= 0 else 0.5, -0.5 if arousal >= 0 else 0.5)
    elif mode == 'amplify':
        return (min(1.0, valence + 0.2), min(1.0, arousal + 0.1))
    elif mode == 'release':
        return (min(0.3, valence + 0.5), max(-0.3, arousal - 0.4))
    elif mode == 'energize':
        return (min(0.4, valence + 0.6), min(0.3, arousal + 0.5))
    return (valence, arousal)


class MusicEmotionRecommender:
    def __init__(self):
        self.calculator = SimilarityCalculator()

    def recommend_music(self, user_emotion, music_data, top_n=10):
        valence, arousal = extract_user_emotion(user_emotion)
        strategy = EmotionStrategy.get_strategy(valence, arousal)
        target_emotion = (strategy['target_valence'], strategy['target_arousal'])

        scored_tracks = []
        for track in music_data:
            tags = track.get('tags', [])
            emotion_vec = build_russell_emotion(tags)
            track_emotion = (emotion_vec['valence'], emotion_vec['arousal'])
            popularity = int(track.get('listeners', 0))
            score = self.calculator.combined_score(track_emotion, target_emotion, popularity)
            scored_tracks.append({'content': track, 'emotion': track_emotion, 'score': score})

        scored_tracks.sort(key=lambda x: x['score'], reverse=True)
        return {'strategy': strategy, 
                'target_emotion': target_emotion, 
                'recommendations': scored_tracks[:top_n]}