# Day by Day 백엔드 API 서버

Django REST Framework 기반의 백엔드 API 서버입니다.

---

## 🚀 빠른 시작

### 필수 요구사항

- **Python 3.13** 이상
- Git

### 1️⃣ 저장소 복제

```bash
git clone <repository-url>
cd Day-by-Day-Backend-Repository
```

### 2️⃣ 패키지 설치

#### 방법 1: Pipenv 사용 (권장)

```bash
pip install pipenv
pipenv install
pipenv shell
```

#### 방법 2: pip 사용

```bash
python -m venv myenv
myenv\Scripts\activate  # Windows
# 또는
source myenv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 3️⃣ 필수 파일 설정

> ⚠️ **중요**: 아래 파일들은 **보안/용량** 이유로 저장소에 포함되지 않습니다. 담당자에게 받아서 설정하세요.

#### 필수 설정 파일

| 파일 경로                                        | 설명                                    | 담당자 |
| ------------------------------------------------ | --------------------------------------- | ------ |
| `daybydaybackend/diary/data/knu_lexicon_ko.json` | 한국어 감정 분석 사전                   | 담당자 |
| `project/.env`                                   | Django 환경 변수 (SECRET_KEY, DEBUG 등) | 담당자 |

#### 파일 설정 방법

1. 담당자로부터 위 파일들을 받기
2. 프로젝트 루트에 해당 위치에 배치
3. `.env` 파일 예시:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4️⃣ 데이터베이스 초기화

```bash
python manage.py migrate
```

### 5️⃣ 서버 실행

```bash
python manage.py runserver
```

접속: http://127.0.0.1:8000

---

## 📁 프로젝트 구조

```
Day-by-Day-Backend-Repository/
├── manage.py                 # Django CLI
├── db.sqlite3               # 개발용 DB
├── requirements.txt         # 의존성 패키지
├── Pipfile                  # Pipenv 설정
├── README.md                # 이 파일
│
├── daybydaybackend/         # 메인 앱
│   ├── accounts/            # 회원 관리
│   ├── books/               # 책 정보
│   ├── diary/               # 일기 관리
│   │   └── data/
│   │       └── knu_lexicon_ko.json  # 필수 파일 ⚠️
│   └── music_movie/         # 음악/영화 추천
│
└── project/                 # Django 설정
    ├── settings.py
    ├── urls.py
    └── wsgi.py
```

---

## 🔧 주요 기능

- **회원 관리**: 회원가입, 로그인, JWT 인증
- **일기 작성**: 감정 분석 기반 일기 관리
- **도서 정보**: 도서 검색 및 추천
- **음악/영화**: 감정별 추천 콘텐츠

---

## 📝 API 문서

서버 실행 후:

- Swagger UI: http://127.0.0.1:8000/swagger/
- ReDoc: http://127.0.0.1:8000/redoc/

---

## ❓ 문제 해결

### 패키지 설치 오류

```bash
# 캐시 삭제 후 재설치
pip cache purge
pip install -r requirements.txt
```

### Python 버전 오류

프로젝트는 **Python 3.13**을 필요로 합니다. 설치 확인:

```bash
python --version
```

### 필수 파일 누락

`ModuleNotFoundError` 또는 `FileNotFoundError`가 발생하면, **필수 파일 설정** 섹션을 다시 확인하세요.

---

## 📞 문의

파일 요청 및 기술 문제는 담당자에게 문의하세요.
