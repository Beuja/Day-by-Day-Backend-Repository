from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # 감정 기반 도서 추천 API
    path('recommend/books/<int:diary_id>/', views.recommend_books_views, name='recommend_books')
]
