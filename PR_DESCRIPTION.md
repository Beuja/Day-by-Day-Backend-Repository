# 📝 Pull Request Description

## 📌 PR Title
**[Feat] 대시보드용 최근 5개 평균 감정 API 및 auto 추천 자율 판정 엔진 탑재 (피드백 기능 배제 및 PR 56 무충돌 선제 통합)**

---

## 📖 개요 (Overview)
본 PR은 유저가 작성한 최근 일기들의 정서적 패턴을 기반으로 대시보드를 시각화하고, 적응형 추천 모드를 자동으로 결정하기 위한 핵심 개인화 API 및 자율 엔진을 탑재합니다.
의사결정에 따라 **피드백 수집 및 선호도 가중치 보정 로직(1번, 2번)은 완벽히 제외**하였으며, **PR 56(상세/목록 조회 및 1일 1회 차단)이 `develop`에 선제 병합되는 시나리오에 대비하여 충돌을 로컬에서 사전에 100% 해결 및 통합 완료**하였습니다.

---

## 🛠️ 주요 작업 내용 (Key Changes)

### 1️⃣ [신설] 대시보드용 최근 5개 평균 감정 분석 API (3번)
- **엔드포인트:** `GET /api/diary/recent-average/`
- **설명:** 유저의 최근 최대 5개 일기 감정 데이터를 추출하여 Plutchik 6대 감정 및 Valence, Arousal 수치를 정교하게 산술 평균하여 반환합니다. 대시보드 정서 추이 그래프 및 시각화 화면에 직접 연동됩니다.

### 2️⃣ [신설] 통계적 분산/평균 기반 추천 모드 자율 판정 엔진 (4번)
- **설명:** 최근 5개 일기의 부정 감정(sadness, anger, fear)의 **평균($\bar{X}$)**과 **표본 분산($S^2$)** 및 연속성 통계를 실시간 분석하여 적응형 기분 모드를 자동으로 결정합니다.
  - **장기적 정서 고착 (Stagnation):** 평균 $\ge 0.35$ 이고 분산 $S^2 < 0.025$ 이거나, 동일 부정 감정이 3회 연속 지배적일 시 ➡️ **`shift` 모드 자율 발동** (기분 전환 중심 추천).
  - **일시적 정서 일탈 (Volatility):** 평균은 높지만 분산 $S^2 \ge 0.025$ 로 급격히 튄 감정 스파이크인 경우 ➡️ **`maintain` 모드 자율 발동** (차분한 감정 유지 및 케어).
  - **긍정 지속 및 극대화:** 긍정 감정(기쁨, 신뢰)의 평균 $\ge 0.3$ 일 시 ➡️ **`amplification` 모드 자율 발동** (활력 고취 및 시너지 극대화).
- **연동:** 통합 추천 API(`get_main_recommendations`) 호출 시 `mode='auto'` 파라미터가 들어오거나 생략될 때 이 엔진이 자동 구동됩니다.

### 3️⃣ [제외/청소] 피드백 관련 일체 로직 및 모델 삭제
- `UserFeedback` 모델, 피드백 등록/수정 API, 취향 통계 프로필 조회 API 및 관련 시리얼라이저를 완벽하게 제거하였습니다.
- 관련 데이터베이스 마이그레이션 파일(`0002_userfeedback.py`)을 물리적으로 완전 삭제하였습니다.
- 추천 엔진들(`books/services.py`, `recommend_music.py`, `recommend_movie.py`, `music_movie/services.py`) 내에 들어있던 싫어요 하드 필터링 및 취향 가중치 선형 결합($V_{target}$) 수식을 모두 걷어내고 순수한 감정 매칭 알고리즘으로 환원하였습니다.

---

## 🚦 PR 56 선제 병합 대비 무충돌 검증 완료 (Conflict Free)
- 사용자가 PR 56을 `develop` 브랜치에 먼저 머지한 뒤 본 브랜치를 병합할 계획이므로, **로컬 상에서 가상 develop 브랜치를 재현(PR 56 선머지 상태)하고 본 브랜치를 머지 테스트하여 충돌 건수 0건으로 완전무결하게 자동 병합(Automatic merge went well)됨을 완벽하게 검증 완료**하였습니다.
- PR 56 머지 후 본 브랜치를 병합하실 때 단 1건의 충돌도 없이 쾌적하게 통합됩니다.

---

## 📂 변경 파일 목록 (Modified Files)
- `daybydaybackend/urls.py` (피드백 API 라우팅 제거)
- `daybydaybackend/diary/models.py` (`UserFeedback` 모델 제거)
- `daybydaybackend/diary/serializers.py` (피드백 시리얼라이저 제거 및 공감/평균 감정 시리얼라이저 통합)
- `daybydaybackend/diary/urls.py` (`recent-average/` 신설 및 PR 56 조회 API 통합)
- `daybydaybackend/diary/views.py` (`get_user_recent_average_emotion_api` 뷰 신설, `auto` 자율 추천 로직 탑재 및 피드백 뷰 삭제)
- `daybydaybackend/diary/services.py` (최근 5개 평균 감정 연산 및 auto 판정 엔진 보존)
- `daybydaybackend/books/services.py` (피드백 가중치 제거, 다양성 벌점 필터 보존)
- `daybydaybackend/music_movie/recommend_music_movie/recommend_music.py` (피드백 가중치 제거, 다양성 벌점 보존)
- `daybydaybackend/music_movie/recommend_music_movie/recommend_movie.py` (피드백 가중치 제거, 다양성 벌점 보존)
- `daybydaybackend/music_movie/services.py` (피드백 반영 로직 청소)
- `daybydaybackend/diary/migrations/0002_userfeedback.py` [DELETED] (피드백 마이그레이션 제거)

---

## 🧪 테스트 및 API 활용 가이드

### 1. 최근 5개 평균 감정 분석 API (대시보드 시각화용)
- **Method:** `GET`
- **Path:** `/api/diary/recent-average/`
- **Headers:** `Authorization: Token <Token값>`

### 2. auto 모드 자율 추천 API
- **Method:** `GET`
- **Path:** `/api/recommend/main/?mode=auto` (또는 mode 파라미터 자체를 생략 시 auto로 기동)
