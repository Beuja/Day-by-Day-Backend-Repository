# ============================================
# 🎯 감정 기반 콘텐츠 추천 시스템
# (2차원 Russell Emotion Model + 외부 감정 사전 버전)
# Gemini 감정 분석 결과 연동
# ============================================

import json
import math
import os
import sys

from collections import defaultdict

# Django 설정 로드
BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        '..'
    )
)
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

import django
django.setup()

from daybydaybackend.diary.services import analyze_emotion_with_gemini

# ============================================
# 🔧 감정 입력 정규화 헬퍼
# ============================================

def extract_user_emotion(user_emotion):
    """
    diary.services.py의 감정 결과 형식과 호환되는 입력을 변환합니다.

    Supported formats:
      - dict: {"valence": float, "arousal": float, "primary_emotion": str}
      - tuple/list: (valence, arousal)
    """
    if isinstance(user_emotion, dict):
        return (
            float(user_emotion.get("valence", 0.0)),
            float(user_emotion.get("arousal", 0.0))
        )

    if isinstance(user_emotion, (list, tuple)) and len(user_emotion) >= 2:
        return (float(user_emotion[0]), float(user_emotion[1]))

    raise ValueError(
        "user_emotion must be a dict or tuple/list containing (valence, arousal)"
    )


# ============================================
# �🔥 외부 감정 사전 import
# ============================================

from emotion_tags import TAG_EMOTION_MAP


# ============================================
# 🎯 태그 기반 Russell 좌표 생성
# ============================================

def build_russell_emotion(tags):

    total_valence = 0
    total_arousal = 0

    matched_count = 0

    for tag in tags:

        tag = tag.lower().strip()

        if tag in TAG_EMOTION_MAP:

            matched_count += 1

            total_valence += \
                TAG_EMOTION_MAP[tag]["valence"]

            total_arousal += \
                TAG_EMOTION_MAP[tag]["arousal"]

    # 태그 매칭 실패 시 중립값
    if matched_count == 0:

        return {

            "valence": 0.0,
            "arousal": 0.0
        }

    # 평균 계산
    valence = total_valence / matched_count
    arousal = total_arousal / matched_count

    # 범위 제한
    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))

    return {

        "valence": round(valence, 3),
        "arousal": round(arousal, 3)
    }


# ============================================
# 🎯 감정 전략 시스템
# ============================================

class EmotionStrategy:

    @staticmethod
    def get_strategy(valence,
                     arousal):

        # 긍정 + 고각성
        if valence > 0 and arousal > 0:

            return {

                "strategy":
                    "amplify",

                "target_valence":
                    min(1.0, valence + 0.2),

                "target_arousal":
                    min(1.0, arousal + 0.1),

                "description":
                    "긍정적 고양감 증폭"
            }

        # 긍정 + 저각성
        elif valence > 0 and arousal <= 0:

            return {

                "strategy":
                    "stabilize",

                "target_valence":
                    valence,

                "target_arousal":
                    arousal,

                "description":
                    "평온한 상태 유지"
            }

        # 부정 + 고각성
        elif valence <= 0 and arousal > 0:

            return {

                "strategy":
                    "release",

                "target_valence":
                    min(0.3, valence + 0.5),

                "target_arousal":
                    max(-0.3, arousal - 0.4),

                "description":
                    "긴장과 스트레스 해소"
            }

        # 부정 + 저각성
        else:

            return {

                "strategy":
                    "energize",

                "target_valence":
                    min(0.4, valence + 0.6),

                "target_arousal":
                    min(0.3, arousal + 0.5),

                "description":
                    "우울 상태 활력 제공"
            }


# ============================================
# 📊 유사도 계산
# ============================================

class SimilarityCalculator:

    @staticmethod
    def cosine_similarity(v1,
                          v2):

        dot_product = \
            v1[0] * v2[0] + \
            v1[1] * v2[1]

        magnitude1 = math.sqrt(
            v1[0]**2 + v1[1]**2
        )

        magnitude2 = math.sqrt(
            v2[0]**2 + v2[1]**2
        )

        if magnitude1 == 0 \
                or magnitude2 == 0:

            return 0.0

        return dot_product / \
            (magnitude1 * magnitude2)

    @staticmethod
    def euclidean_distance(v1,
                           v2):

        return math.sqrt(

            (v1[0] - v2[0])**2 +

            (v1[1] - v2[1])**2
        )

    @staticmethod
    def combined_score(current,
                       target,
                       popularity=0,
                       cosine_weight=0.6):

        cos_sim = \
            SimilarityCalculator \
            .cosine_similarity(
                current,
                target
            )

        distance = \
            SimilarityCalculator \
            .euclidean_distance(
                current,
                target
            )

        distance_score = \
            1 / (1 + distance)

        emotion_score = \
            cosine_weight * cos_sim + \
            (1 - cosine_weight) \
            * distance_score

        popularity_score = \
            min(1.0,
                popularity / 1000000)

        final_score = \
            emotion_score * 0.8 + \
            popularity_score * 0.2

        return round(final_score, 4)


# ============================================
# 🎵🎬 추천 시스템
# ============================================

class EmotionRecommender:

    def __init__(self):

        self.calculator = \
            SimilarityCalculator()

    # ========================================
    # 🎵 음악 추천
    # ========================================

    def recommend_music(self,
                        user_emotion,
                        music_data,
                        top_n=10):

        valence, arousal = extract_user_emotion(user_emotion)

        strategy = \
            EmotionStrategy.get_strategy(

                valence,
                arousal
            )

        target_emotion = (

            strategy["target_valence"],
            strategy["target_arousal"]
        )

        scored_tracks = []

        for track in music_data:

            tags = track.get("tags", [])

            emotion_vec = \
                build_russell_emotion(tags)

            track["emotion_vector"] = emotion_vec

            track_emotion = (

                emotion_vec["valence"],
                emotion_vec["arousal"]
            )

            popularity = int(

                track.get(
                    "listeners",
                    0
                )
            )

            score = \
                self.calculator \
                .combined_score(

                    track_emotion,

                    target_emotion,

                    popularity
                )

            scored_tracks.append({

                "content":
                    track,

                "emotion":
                    track_emotion,

                "score":
                    score
            })

        scored_tracks.sort(

            key=lambda x:
                x["score"],

            reverse=True
        )

        return {

            "strategy":
                strategy,

            "target_emotion":
                target_emotion,

            "recommendations":
                scored_tracks[:top_n]
        }

    # ========================================
    # 🎬 영화 추천
    # ========================================

    def recommend_movies(self,
                         user_emotion,
                         movie_data,
                         top_n=10):

        valence, arousal = extract_user_emotion(user_emotion)

        strategy = \
            EmotionStrategy.get_strategy(

                valence,
                arousal
            )

        target_emotion = (

            strategy["target_valence"],
            strategy["target_arousal"]
        )

        scored_movies = []

        for movie in movie_data:

            tags = movie.get("tags", [])

            emotion_vec = \
                build_russell_emotion(tags)

            movie["emotion_vector"] = emotion_vec

            movie_emotion = (

                emotion_vec["valence"],
                emotion_vec["arousal"]
            )

            popularity = float(

                movie.get(
                    "popularity",
                    0
                )
            )

            score = \
                self.calculator \
                .combined_score(

                    movie_emotion,

                    target_emotion,

                    popularity
                )

            scored_movies.append({

                "content":
                    movie,

                "emotion":
                    movie_emotion,

                "score":
                    score
            })

        scored_movies.sort(

            key=lambda x:
                x["score"],

            reverse=True
        )

        return {

            "strategy":
                strategy,

            "target_emotion":
                target_emotion,

            "recommendations":
                scored_movies[:top_n]
        }


# ============================================
# 🔗 diary.services.py 연동 헬퍼
# ============================================

def recommend_content_by_emotion_result(
    emotion_result,
    music_data,
    movie_data,
    top_n=10
):
    """
    diary.services.py의 감정 결과 형식과 호환되는 추천 결과를 생성합니다.
    """
    recommender = EmotionRecommender()

    return {
        "user_emotion": emotion_result,
        "music": recommender.recommend_music(
            emotion_result,
            music_data,
            top_n
        ),
        "movies": recommender.recommend_movies(
            emotion_result,
            movie_data,
            top_n
        )
    }


# ============================================
# �🚀 메인 실행
# ============================================

def main():

    print("=" * 70)
    print("🎯 감정 기반 콘텐츠 추천 시스템")
    print("=" * 70)

    # ========================================
    # 📥 DB 로드
    # ========================================

    with open(
        "music_database.json",
        "r",
        encoding="utf-8"
    ) as f:

        music_data = json.load(f)

    with open(
        "movie_database.json",
        "r",
        encoding="utf-8"
    ) as f:

        movie_data = json.load(f)

    print(
        f"\n✅ 음악 데이터:"
        f" {len(music_data)}곡"
    )

    print(
        f"✅ 영화 데이터:"
        f" {len(movie_data)}편"
    )

    # ========================================
    # 🔥 diary.services.py 감정 분석 결과 입력
    # ========================================

    sample_diary_text = (
        "오늘 하루는 기분이 좋았고, 친구와 함께 웃으면서 산책을 했습니다. "
        "작은 성취를 느껴서 마음이 안정되고 행복했습니다."
    )

    emotion_result = analyze_emotion_with_gemini(sample_diary_text)

    if not isinstance(emotion_result, dict):
        emotion_result = {
            "valence": 0.0,
            "arousal": 0.0,
            "primary_emotion": "분석불가"
        }

    user_emotion = extract_user_emotion(emotion_result)

    print("\n📊 사용자 감정")

    print(
        f"감정:"
        f" {emotion_result['primary_emotion']}"
    )

    print(
        f"V={user_emotion[0]}, "
        f"A={user_emotion[1]}"
    )

    recs = recommend_content_by_emotion_result(
        emotion_result,
        music_data,
        movie_data,
        top_n=10
    )

    music_rec = recs["music"]
    movie_rec = recs["movies"]

    # ========================================
    # 🎵 음악 결과
    # ========================================

    print("\n" + "=" * 70)
    print("🎵 음악 추천")
    print("=" * 70)

    print(
        f"\n🎯 전략:"
        f" {music_rec['strategy']['strategy']}"
    )

    print(
        f"📝 "
        f"{music_rec['strategy']['description']}"
    )

    print(
        f"🎯 목표 감정:"
        f" V={music_rec['target_emotion'][0]:+.2f},"
        f" A={music_rec['target_emotion'][1]:+.2f}"
    )

    print("\n🎵 Top 10\n")

    for i, item in enumerate(

            music_rec["recommendations"],
            1):

        track = item["content"]

        print(

            f"{i:2d}. "

            f"{track.get('title')} "

            f"- "

            f"{track.get('artist')}"
        )

        print(

            f"    감정:"
            f" V={item['emotion'][0]:+.2f},"
            f" A={item['emotion'][1]:+.2f}"

            f" | 점수: {item['score']:.3f}"
        )

        print(
            f"    태그:"
            f" {track.get('tags', [])}"
        )

    # ========================================
    # 🎬 영화 결과
    # ========================================

    print("\n" + "=" * 70)
    print("🎬 영화 추천")
    print("=" * 70)

    print(
        f"\n🎯 전략:"
        f" {movie_rec['strategy']['strategy']}"
    )

    print(
        f"📝 "
        f"{movie_rec['strategy']['description']}"
    )

    print(
        f"🎯 목표 감정:"
        f" V={movie_rec['target_emotion'][0]:+.2f},"
        f" A={movie_rec['target_emotion'][1]:+.2f}"
    )

    print("\n🎬 Top 10\n")

    for i, item in enumerate(

            movie_rec["recommendations"],
            1):

        movie = item["content"]

        print(

            f"{i:2d}. "

            f"{movie.get('title')}"

        )

        print(

            f"    감정:"
            f" V={item['emotion'][0]:+.2f},"
            f" A={item['emotion'][1]:+.2f}"

            f" | 점수: {item['score']:.3f}"
        )

        print(
            f"    태그:"
            f" {movie.get('tags', [])}"
        )

    # ========================================
    # 💾 저장
    # ========================================

    result = {

        "user_emotion":
            emotion_result,

        "music":
            music_rec,

        "movies":
            movie_rec
    }

    with open(

        "recommendation_result.json",

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            result,

            f,

            ensure_ascii=False,

            indent=2
        )

    print(
        "\n💾 recommendation_result.json 저장 완료"
    )


if __name__ == "__main__":
    main()