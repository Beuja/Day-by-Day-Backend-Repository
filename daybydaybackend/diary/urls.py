from django.urls import path
from . import views

app_name = 'diary'

urlpatterns = [
    # 일기를 작성해서 DB에 저장하는 API
    path('create/', views.create_diary, name='create_diary'),

    # 일기를 ai 한테 보내는 API (Diary + Gemini API 기반 감정 추출)
    path('send/', views.analyze_diary_emotion, name='analyze_diary_emotion'),

    # 캘린더 전용 월별 감정 조회 API (Option A 해시맵 방식)
    path('calendar/', views.get_calendar_view, name='get_calendar_view'),

    # 대시보드용 최근 5개 평균 감정 분석 API
    path('recent-average/', views.get_user_recent_average_emotion_api, name='get_user_recent_average_emotion'),
]
