from django.contrib import admin
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('isbn', 'title', 'author', 'category', 'valence', 'arousal')
    list_filter = ('category', 'valence', 'arousal')
    search_fields = ('title', 'author', 'isbn')
    ordering = ('-title',)
