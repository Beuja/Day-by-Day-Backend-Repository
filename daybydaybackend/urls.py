from django.urls import path, include

urlpatterns = [
    # 인증 관련 API
    path('auth/', include('daybydaybackend.accounts.urls')),

    # 일기 관련 API
    path('diary/', include('daybydaybackend.diary.urls')),

    # 도서 추천 API
    path('books/', include('daybydaybackend.books.urls')),

    # 음악/영화 추천 API
    path('music-movie/', include('daybydaybackend.music_movie.urls')),
]