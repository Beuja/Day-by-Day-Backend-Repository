from django.contrib import admin
from django.urls import path, include
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Day by Day API",
        default_version='1.0',
        description="Day by Day 프로젝트의 API 문서입니다.",
    ),
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API 엔드포인트 (기능별 라우팅)
    path('api/', include([
        # 인증 관련 API
        path('auth/', include('daybydaybackend.accounts.urls')),
        
        # 일기 관련 API
        path('diary/', include('daybydaybackend.diary.urls')),
        
        # 도서 추천 API
        path('books/', include('daybydaybackend.books.urls')),
        
        # 음악/영화 추천 API
        path('music-movie/', include('daybydaybackend.music_movie.urls')),
    ])),

    # swagger 문서 URL (개발자용)
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # redoc 문서 URL (개발자용)
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]