# 📝 Pull Request Description (feature/jung)

## 📌 PR Title
**[Feat] 1일 1회 일기 가드, 추천 콘텐트 날짜/다이어리 ID 매핑 및 과거 일기 데이터 시더(load_diary_data) 고도화**

---

## 📖 개요 (Overview)
본 PR은 DDB(Day by Day Book) 서비스의 데이터 정합성을 고도화하고 프론트엔드 연동을 원활히 지원하기 위한 핵심 백엔드 인프라를 구축합니다.
하루 한 번만 일기 작성을 허용하는 강력한 중복 방지 시스템, 추천 콘텐츠와 작성 일기 간의 1:1 결속 매핑 데이터 주입, 카테고리 중복 방지 다양성 필터, 그리고 월별 캘린더 및 통계 대시보드 검증을 위한 대량의 과거 일기 더미데이터 적재 도구(`load_diary_data`)를 완비하였습니다.

---

## 🛠️ 주요 작업 내용 (Key Changes)

### 1️⃣ 1일 1회 일기 작성 제한 및 직관적 플래그 (is_diary) 제공
- **설명:** 동일 날짜(오늘 00:00 ~ 23:59)에 유저가 이미 일기를 작성한 이력이 있다면, API 요청을 차단하고 `HTTP 400` 상태코드와 함께 `{"is_diary": true}`를 반환합니다. (이미 작성되어 있으므로 true)
- **성공 반환:** 성공적으로 작성된 경우 `{"is_diary": true}` 플래그를 추가로 동적 주입하여 반환함으로써 프론트엔드가 자연스럽게 일기 작성 화면 및 제어를 수행하도록 도왔습니다.
- **서버 환경 대응:** `USE_TZ = False` 및 SQLite 환경에서 Timezone 오류(`ValueError`)가 발생하지 않도록 naive datetime 시간 범위를 활용해 완벽하게 대응하였습니다.

### 2️⃣ 글로벌 추천 생성/조회 시 1:1 매핑 데이터 주입
- **설명:** 책, 음악, 영화의 개별 추천 생성 및 통합 추천(`recommend/main/`) API 조회 결과를 개조하여, 각각의 추천 객체마다 **`diary_id`**와 **`recommend_date`**를 동적으로 바인딩하여 1:1 매핑 정합성을 완성하였습니다.
- **효과:** 프론트엔드에서 특정 추천 데이터를 누를 때 해당 추천이 유래된 과거 특정 날짜의 일기 카드로 부드럽게 화면을 제어하고 전환할 수 있습니다.

### 3️⃣ 추천 카테고리 기준 다양성(Diversity) 증진 알고리즘 탑재
- **설명:** 유저에게 너무 유사한 카테고리만 추천되어 정서적 권태를 느끼는 현상을 예방하고자, 과거 5회의 추천 이력을 실시간 트래킹하여 중복 장르 및 카테고리에 벌점(Penalty)을 가산합니다.
  - **도서:** `category` 중복 시 **벌점 +0.3** 부여
  - **음악:** `tags` 중복 시 **벌점 +0.2** 부여
  - **영화:** `genre` 중복 시 **벌점 +0.25** 부여
- **효과:** 중복도가 높은 음악의 순위가 후순위(예: 160위권에서 400위권)로 자연스럽게 격하되어 극도로 다채로운 추천 결과를 보장합니다.

### 4️⃣ 일기 목록 및 단일 상세 조회 API 신설
- **목록 조회:** `GET /api/diary/` (유저가 쓴 모든 일기를 최신순으로 최적화 조회)
- **상세 조회:** `GET /api/diary/<int:diary_id>/` (보안을 가미해 타인의 일기 조회는 철저히 차단하고 본인의 단일 일기와 1:1 매치된 감정 정보 반환)

### 5️⃣ 고해상도 과거 일기 더미데이터 일괄 적재 장고 CLI 커맨드 구축
- **명령어:** `python manage.py load_diary_data --username=testuser --days=30`
- **설명:** 7대 감정(기쁨, 슬픔, 분노, 두려움, 신뢰, 놀람, 평온)별로 다채롭고 자연스럽게 작성된 32개의 한국어 일기 시나리오 데이터셋(`diary_data.json`)을 구축하여, 하루씩 소급 적용하여 DB에 안전하게 일괄 이식해 줍니다.
- **추천 연동:** 데이터를 적재할 때, 단순히 일기만 들어가는 것이 아니라 해당 감정에 딱 들어맞는 책, 음악, 영화 추천 관계(`DailyRecommended`)까지 1:1로 함께 무작위 추출하여 실감 나게 바인딩해 줌으로써 프론트엔드 실전 시각화 테스트가 가능합니다.

---

## 📂 변경 파일 목록 (Modified Files)
- `daybydaybackend/diary/models.py` (`DailyRecommended` 등 관계 매핑 보존)
- `daybydaybackend/diary/serializers.py` (`DiaryEmpathyResponseSerializer` 및 목록/상세용 직렬화 구조 정착)
- `daybydaybackend/diary/urls.py` (상세/목록 및 공감 멘트 엔드포인트 등록)
- `daybydaybackend/diary/views.py` (`create_diary` 내 1일 1회 가드 탑재, 조회 API 구현 및 추천 1:1 매핑 반환)
- `daybydaybackend/books/services.py` (과거 추천 도서 카테고리 중복 시 벌점 +0.3 스코어 강등 패널티 구현)
- `daybydaybackend/music_movie/recommend_music_movie/recommend_music.py` (중복 태그 벌점 +0.2 패널티 구현)
- `daybydaybackend/music_movie/recommend_music_movie/recommend_movie.py` (중복 장르 벌점 +0.25 패널티 구현)
- `daybydaybackend/diary/data/diary_data.json` [NEW] (고해상도 일기 시나리오 원본 데이터)
- `daybydaybackend/diary/management/commands/load_diary_data.py` [NEW] (과거 일기 및 추천 데이터 일괄 자동 마이그레이션 커맨드)

---

## 🧪 정합성 및 무결성 테스트 완료
- KST naive 1일 1회 차단망 및 `is_diary` 제어 플래그 작동 검증 완료.
- 조회 API의 404 소유권 격리 차단성 입증 완료.
- 카테고리 다양성 벌점 랭킹 격하 필터 정밀 작동 검증 완료.
