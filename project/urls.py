from django.contrib import admin
from django.urls import path, include
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Day by Day API",
        default_version='v1',
        description="Day by Day 프로젝트의 API 문서입니다.",
    ),
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('daybydaybackend.urls')),

    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    #path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]