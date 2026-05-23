import math

from .emotion_tags import TAG_EMOTION_MAP


ORDERED_KEYS = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']


def build_6d_emotion_vector(tags):
    total_vector = {key: 0.0 for key in ORDERED_KEYS}
    matched_count = 0

    for tag in tags:
        tag = str(tag).lower().strip()
        if tag in TAG_EMOTION_MAP:
            matched_count += 1
            tag_vec = TAG_EMOTION_MAP[tag]
            for key in ORDERED_KEYS:
                total_vector[key] += tag_vec.get(key, 0.0)

    if matched_count == 0:
        return [0.0] * 6

    return [round(total_vector[key] / matched_count, 4) for key in ORDERED_KEYS]


def convert_emotion_vector_to_6d(emotion_vector):
    return [
        round(max(0.0, min(1.0, emotion_vector.get('joy', 0) * 1.0 + emotion_vector.get('romance', 0) * 0.6)), 4),
        round(max(0.0, min(1.0, emotion_vector.get('sadness', 0) * 1.0 + emotion_vector.get('darkness', 0) * 0.5)), 4),
        round(max(0.0, min(1.0, emotion_vector.get('anger', 0) * 1.0)), 4),
        round(max(0.0, min(1.0, emotion_vector.get('fear', 0) * 1.0 + emotion_vector.get('darkness', 0) * 0.3)), 4),
        round(max(0.0, min(1.0, emotion_vector.get('trust', 0) * 1.0 + emotion_vector.get('calmness', 0) * 0.8 + emotion_vector.get('dreaminess', 0) * 0.4)), 4),
        round(max(0.0, min(1.0, emotion_vector.get('surprise', 0) * 1.0 + emotion_vector.get('energy', 0) * 0.5)), 4),
    ]


def build_content_6d_emotion_vector(content):
    emotion_vector = content.get('emotion_vector')
    if isinstance(emotion_vector, dict) and emotion_vector:
        return convert_emotion_vector_to_6d(emotion_vector)

    return build_6d_emotion_vector(content.get('tags', []))


def get_direction_weights(u_vec, mode):
    weights = [1.0] * 6

    if mode == 'maintain':
        return weights

    if mode == 'shift':
        weights[0] = 0.5
        weights[1] = 2.0
        weights[2] = 2.0
        weights[3] = 2.0
        weights[4] = 0.5
        weights[5] = 1.0
    elif mode == 'amplification':
        max_val = max(u_vec)
        max_emotion_idx = u_vec.index(max_val)
        weights[max_emotion_idx] = 0.2

    return weights


def calculate_weighted_euclidean(u_vec, b_vec, w_vec):
    euclidean_dist = math.sqrt(sum(w * ((u - b) ** 2) for u, b, w in zip(u_vec, b_vec, w_vec)))
    sum_w = sum(w_vec)
    max_euclidean = math.sqrt(sum(w * sum_w for w in w_vec))

    if max_euclidean == 0:
        return 0.0

    return euclidean_dist / max_euclidean


def calculate_cosine_distance(u_vec, b_vec, u_norm):
    b_norm = math.sqrt(sum(b ** 2 for b in b_vec))

    if b_norm == 0:
        b_norm = 1e-9

    dot_product = sum(u * b for u, b in zip(u_vec, b_vec))
    cosine_sim = dot_product / (u_norm * b_norm)
    return 1.0 - cosine_sim