from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # 감정 기반 도서 추천 API
    path('recommend/', views.recommend_books, name='recommend_books'),
]
