# Day-by-Day Backend — 감정 기반 추천 백엔드

이 저장소는 사용자의 일기 텍스트를 분석해 감정 기반으로 도서·음악·영화 추천을 제공하는 Django 백엔드입니다.

## 프로젝트 개요

- 목적: 일기 감정 분석을 통해 개인화된 추천을 생성하고 저장/복원 기능을 제공
- 주요 기능: 일기 작성/감정 분석, 6차원 감정벡터 기반 추천(도서·음악·영화), 추천 저장/복원, Swagger API

## 팀 구성

- (추후 추가)

## 기술 스택

- Django (REST API)
- kiwi 라이브러리(오픈소스)

## 주요 기능

1. 일기 감정 분석

- 일기 텍스트에서 6차원 감정 벡터(joy, sadness, anger, fear, trust, surprise) 및 2D(valence/arousal) 계산
- 분석 파이프라인: `daybydaybackend/diary/emotion_analyzer.py` 등

1. 추천 엔진

- 6D 감정벡터로 도서/음악/영화 추천
- 추천 전략(mode): `maintain`, `shift`, `amplification`

1. 저장 및 복원

- 추천 결과를 `DailyRecommended` 모델로 저장, 달력 조회 시 복원 지원

## 설치 및 실행(간단)

```bash
python -m venv myenv
myenv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 환경변수/설정

- `project/settings.py`는 환경변수(.env 또는 플랫폼 환경변수)를 사용하도록 구성 권장
- 예: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `GEMINI_API_KEY`, `ALADIN_TTB_KEY`

## 중요 데이터 파일

- `daybydaybackend/diary/data/knu_lexicon_ko.json` (한국어 감정사전)
- `daybydaybackend/music_movie/data/music_database.json`, `movie_database.json` (추천 데이터)
