# ============================================
# 🧠 태그 감정 사전
# ============================================

TAG_EMOTION_MAP = {

    # ========================================
    # 긍정 / 행복
    # ========================================

    "happy": {
        "joy": 0.9,
        "energy": 0.7
    },

    "upbeat": {
        "joy": 0.8,
        "energy": 0.8
    },

    "fun": {
        "joy": 0.8,
        "energy": 0.7
    },

    "summer": {
        "joy": 0.7,
        "calmness": 0.3
    },

    "dance": {
        "energy": 0.9,
        "joy": 0.6
    },

    "party": {
        "energy": 1.0,
        "joy": 0.7
    },

    "catchy": {
        "joy": 0.5,
        "energy": 0.4
    },

    "pop": {
        "joy": 0.5,
        "energy": 0.5
    },

    # ========================================
    # 슬픔
    # ========================================

    "sad": {
        "sadness": 0.9,
        "darkness": 0.5
    },

    "melancholy": {
        "sadness": 0.8,
        "nostalgia": 0.7
    },

    "heartbreak": {
        "sadness": 0.9,
        "romance": 0.4
    },

    "depression": {
        "sadness": 1.0,
        "darkness": 0.8
    },

    "lonely": {
        "sadness": 0.8,
        "dreaminess": 0.4
    },

    "emotional": {
        "sadness": 0.6,
        "romance": 0.3
    },

    # ========================================
    # 차분함
    # ========================================

    "calm": {
        "calmness": 0.9,
        "dreaminess": 0.3
    },

    "mellow": {
        "calmness": 0.8,
        "dreaminess": 0.5
    },

    "acoustic": {
        "calmness": 0.6,
        "nostalgia": 0.4
    },

    "ambient": {
        "dreaminess": 0.8,
        "calmness": 0.7
    },

    "beautiful": {
        "dreaminess": 0.6,
        "romance": 0.4
    },

    "dream pop": {
        "dreaminess": 0.9,
        "sadness": 0.3
    },

    # ========================================
    # 강렬함
    # ========================================

    "rock": {
        "energy": 0.7,
        "anger": 0.2
    },

    "alternative rock": {
        "energy": 0.6,
        "dreaminess": 0.2
    },

    "punk": {
        "anger": 0.7,
        "energy": 0.9
    },

    "metal": {
        "anger": 0.9,
        "darkness": 0.7
    },

    "aggressive": {
        "anger": 1.0,
        "energy": 0.8
    },

    # ========================================
    # 로맨스
    # ========================================

    "love": {
        "romance": 0.9,
        "joy": 0.5
    },

    "romantic": {
        "romance": 1.0,
        "dreaminess": 0.4
    },

    # ========================================
    # 향수
    # ========================================

    "90s": {
        "nostalgia": 0.8
    },

    "80s": {
        "nostalgia": 0.9
    },

    "70s": {
        "nostalgia": 0.7
    },

    "oldies": {
        "nostalgia": 1.0
    },

    # ========================================
    # 어두움
    # ========================================

    "dark": {
        "darkness": 1.0,
        "fear": 0.4
    },

    "emo": {
        "sadness": 0.8,
        "darkness": 0.7
    },

    "gothic": {
        "darkness": 0.9,
        "dreaminess": 0.4
    },

   # ========================================
# 🎬 영화 키워드 추가
# ========================================

# 범죄 / 스릴러
"murder": {
    "fear": 0.7,
    "darkness": 0.8
},

"serial killer": {
    "fear": 0.9,
    "darkness": 1.0
},

"crime": {
    "anger": 0.4,
    "darkness": 0.6
},

"detective": {
    "fear": 0.3,
    "dreaminess": 0.2
},

"investigation": {
    "fear": 0.4,
    "energy": 0.4
},

"prison": {
    "sadness": 0.6,
    "darkness": 0.7
},

"mafia": {
    "anger": 0.7,
    "darkness": 0.8
},

"gangster": {
    "anger": 0.8,
    "energy": 0.5
},

"revenge": {
    "anger": 0.8,
    "darkness": 0.5
},

"betrayal": {
    "sadness": 0.7,
    "anger": 0.5
},

"conspiracy": {
    "fear": 0.6,
    "darkness": 0.5
},

"spy": {
    "energy": 0.7,
    "fear": 0.3
},

# 호러
"monster": {
    "fear": 0.8,
    "darkness": 0.7
},

"ghost": {
    "fear": 0.9,
    "dreaminess": 0.4
},

"zombie": {
    "fear": 0.9,
    "energy": 0.7
},

"vampire": {
    "darkness": 0.9,
    "romance": 0.2
},

"demon": {
    "fear": 1.0,
    "darkness": 1.0
},

"haunted house": {
    "fear": 0.9,
    "darkness": 0.8
},

"survival": {
    "fear": 0.7,
    "energy": 0.6
},

"post-apocalyptic": {
    "sadness": 0.6,
    "darkness": 0.9
},

# 액션
"battle": {
    "energy": 0.9,
    "anger": 0.5
},

"war": {
    "anger": 0.7,
    "sadness": 0.5
},

"sword fight": {
    "energy": 0.8,
    "anger": 0.4
},

"martial arts": {
    "energy": 0.9,
    "joy": 0.2
},

"superhero": {
    "joy": 0.6,
    "energy": 0.9
},

"explosion": {
    "energy": 1.0,
    "fear": 0.3
},

"chase": {
    "energy": 0.9,
    "fear": 0.4
},

# SF / 판타지
"space": {
    "dreaminess": 0.7,
    "fear": 0.2
},

"alien": {
    "fear": 0.6,
    "dreaminess": 0.7
},

"time travel": {
    "dreaminess": 0.9,
    "nostalgia": 0.4
},

"future": {
    "dreaminess": 0.6,
    "fear": 0.2
},

"cyberpunk": {
    "darkness": 0.7,
    "dreaminess": 0.6
},

"robot": {
    "dreaminess": 0.5,
    "calmness": 0.1
},

"virtual reality": {
    "dreaminess": 0.8,
    "fear": 0.3
},

"magic": {
    "dreaminess": 0.9,
    "joy": 0.4
},

"wizard": {
    "dreaminess": 0.9,
    "joy": 0.3
},

"dragon": {
    "dreaminess": 0.8,
    "fear": 0.4
},

"kingdom": {
    "dreaminess": 0.6,
    "nostalgia": 0.2
},

"mythology": {
    "dreaminess": 0.8,
    "darkness": 0.2
},

# 드라마
"family": {
    "calmness": 0.6,
    "romance": 0.2
},

"friendship": {
    "joy": 0.7,
    "calmness": 0.4
},

"school": {
    "nostalgia": 0.5,
    "joy": 0.3
},

"coming of age": {
    "nostalgia": 0.8,
    "sadness": 0.2
},

"youth": {
    "joy": 0.5,
    "nostalgia": 0.6
},

"life": {
    "calmness": 0.4,
    "sadness": 0.2
},

"death": {
    "sadness": 1.0,
    "darkness": 0.7
},

"hospital": {
    "sadness": 0.6,
    "fear": 0.3
},

"marriage": {
    "romance": 0.8,
    "calmness": 0.3
},

"divorce": {
    "sadness": 0.8,
    "anger": 0.2
},

# 로맨스
"love triangle": {
    "romance": 0.9,
    "sadness": 0.4
},

"first love": {
    "romance": 1.0,
    "nostalgia": 0.6
},

"kissing": {
    "romance": 0.9,
    "joy": 0.4
},

"wedding": {
    "romance": 0.9,
    "joy": 0.6
},

"breakup": {
    "sadness": 0.9,
    "romance": 0.5
},

# 모험
"adventure": {
    "energy": 0.7,
    "joy": 0.5
},

"treasure": {
    "joy": 0.7,
    "energy": 0.5
},

"journey": {
    "dreaminess": 0.5,
    "nostalgia": 0.3
},

"island": {
    "calmness": 0.6,
    "dreaminess": 0.4
},

"ocean": {
    "calmness": 0.7,
    "dreaminess": 0.5
},

# 감성 / 분위기
"winter": {
    "sadness": 0.3,
    "calmness": 0.5
},

"rain": {
    "sadness": 0.5,
    "dreaminess": 0.5
},

"night": {
    "darkness": 0.5,
    "dreaminess": 0.4
},

"moon": {
    "dreaminess": 0.8,
    "calmness": 0.4
},

"music": {
    "joy": 0.5,
    "nostalgia": 0.4
},

"dancing": {
    "joy": 0.8,
    "energy": 0.8
},

"christmas": {
    "joy": 0.9,
    "nostalgia": 0.7
},

"summer vacation": {
    "joy": 0.8,
    "nostalgia": 0.5
}
}