from django.urls import path
from . import views

app_name = 'diary'

urlpatterns = [
    # 일기를 작성해서 DB에 저장하는 API
    path('create/', views.create_diary, name='create_diary'),

    # 일기를 ai 한테 보내는 API (Diary + Gemini API 기반 감정 추출)
    path('send/', views.analyze_diary_emotion, name='analyze_diary_emotion'),
]
