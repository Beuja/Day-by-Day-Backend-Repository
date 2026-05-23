import math

from ._emotion_recommendation_common import (
    ORDERED_KEYS,
    build_content_6d_emotion_vector,
    calculate_cosine_distance,
    calculate_weighted_euclidean,
    get_direction_weights,
)


class MovieEmotionRecommender:
    def recommend_movies(self, user_emotion, movie_data, mode='maintain', top_n=3):
        u_vec = [float(user_emotion.get(key, 0.0)) for key in ORDERED_KEYS]
        u_norm = math.sqrt(sum(u ** 2 for u in u_vec))
        if u_norm == 0:
            u_norm = 1e-9

        w_vec = get_direction_weights(u_vec, mode)

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

        for movie in movie_data:
            orig_tags = movie.get('tags', [])
            b_vec = build_content_6d_emotion_vector(movie)

            pure_distance = math.sqrt(sum((u - b) ** 2 for u, b in zip(u_vec, b_vec)))

            if pure_distance <= radius_limit:
                norm_euclidean = calculate_weighted_euclidean(u_vec, b_vec, w_vec)
                cosine_dist = calculate_cosine_distance(u_vec, b_vec, u_norm)

                emotion_score = (alpha * norm_euclidean) + ((1 - alpha) * cosine_dist)

                popularity = float(movie.get('popularity', 0.0))
                popularity_score = min(1.0, popularity / 100000)
                final_score = (emotion_score * 0.8) + ((1.0 - popularity_score) * 0.2)

                filtered_and_scored.append({
                    'movie_id': movie.get('movie_id', movie.get('id')),
                    'title': movie.get('title'),
                    'director': movie.get('director'),
                    'image_url': movie.get('image_url', ''),
                    'tags': orig_tags,
                    'score': round(final_score, 4),
                })

        filtered_and_scored.sort(key=lambda x: x['score'])

        return {
            'mode': mode,
            'radius_limit': radius_limit,
            'recommendations': filtered_and_scored[:top_n],
        }