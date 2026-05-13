from django.contrib import admin
from .models import Music, Movie


@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'valence', 'arousal', 'playcount')
    list_filter = ('source_tag', 'valence', 'arousal')
    search_fields = ('title', 'artist')
    ordering = ('-playcount',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'valence', 'arousal', 'vote_average', 'popularity')
    list_filter = ('genre', 'valence', 'arousal', 'release_date')
    search_fields = ('title', 'overview')
    ordering = ('-popularity',)
