from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # 감정 기반 도서 추천 API (뷰 함수 시그니처 및 POST 요청 형식에 최적화)
    path('recommend/books/', views.recommend_books_views, name='recommend_books')
]
