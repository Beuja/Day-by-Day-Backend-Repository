from django.contrib import admin
from .models import Diary, DiaryEmotion

# 일기 관리 모델
@admin.register(Diary)
class DiaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'short_content', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('content', 'user__username')
    ordering = ('-created_at',)

    def short_content(self, obj):
        # 일기 내용이 너무 길면 관리자 페이지가 깨지므로 앞부분만 표시
        return obj.content[:30] + '...' if len(obj.content) > 30 else obj.content
    short_content.short_description = '일기 내용 요약'

# 일기 감정 분석 결과 관리 모델
@admin.register(DiaryEmotion)
class DiaryEmotionAdmin(admin.ModelAdmin):
    list_display = ('id', 'diary_link', 'primary_emotion', 'valence', 'arousal')
    list_filter = ('primary_emotion',)
    search_fields = ('primary_emotion', 'diary__content')

    def diary_link(self, obj):
        # 어떤 일기인지 아이디와 요약을 보여줍니다
        return f"일기 #{obj.diary.id}: {obj.diary.content[:15]}..."
    diary_link.short_description = '연결된 일기'

