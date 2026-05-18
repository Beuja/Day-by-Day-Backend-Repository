import json
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.music_movie.models import Music, Movie
from daybydaybackend.music_movie.services import convert_emotion_vector_to_russell
import os


class Command(BaseCommand):
    help = "JSON 파일에서 음악 및 영화 데이터 로드"

    def handle(self, *args, **options):
        # 데이터 파일 경로
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        package_dir = os.path.join(base_dir, 'recommend_music_movie')
        music_file = os.path.join(package_dir, 'music_database.json')
        movie_file = os.path.join(package_dir, 'movie_database.json')

        # 음악 데이터 로드
        if os.path.exists(music_file):
            self.stdout.write("음악 데이터 로드 중...")
            try:
                with open(music_file, 'r', encoding='utf-8') as f:
                    music_data = json.load(f)
                
                music_count = 0
                for item in music_data:
                    if item.get('type') == 'music':
                        # 10차원 감정 벡터를 2차원으로 변환
                        emotion_vector = item.get('emotion_vector', {})
                        valence, arousal = convert_emotion_vector_to_russell(emotion_vector)
                        
                        Music.objects.get_or_create(
                            title=item.get('title'),
                            artist=item.get('artist', ''),
                            defaults={
                                'source_tag': item.get('source_tag', ''),
                                'listeners': item.get('listeners', 0),
                                'playcount': item.get('playcount', 0),
                                'tags': item.get('tags', []),
                                'emotion_vector': emotion_vector,
                                'valence': valence,
                                'arousal': arousal,
                            }
                        )
                        music_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"✓ {music_count}개의 음악 로드 완료!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"음악 로드 오류: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"음악 파일 없음: {music_file}"))

        # 영화 데이터 로드
        if os.path.exists(movie_file):
            self.stdout.write("영화 데이터 로드 중...")
            try:
                with open(movie_file, 'r', encoding='utf-8') as f:
                    movie_data = json.load(f)
                
                movie_count = 0
                for item in movie_data:
                    if item.get('type') == 'movie':
                        emotion_vector = item.get('emotion_vector', {})
                        valence, arousal = convert_emotion_vector_to_russell(emotion_vector)
                        
                        Movie.objects.get_or_create(
                            tmdb_id=item.get('id'),
                            defaults={
                                'title': item.get('title'),
                                'genre': item.get('genre', ''),
                                'overview': item.get('overview', ''),
                                'vote_average': item.get('vote_average'),
                                'vote_count': item.get('vote_count', 0),
                                'popularity': item.get('popularity', 0),
                                'release_date': item.get('release_date'),
                                'poster_path': item.get('poster_path', ''),
                                'valence': valence,
                                'arousal': arousal,
                            }
                        )
                        movie_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"✓ {movie_count}개의 영화 로드 완료!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"영화 로드 오류: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"영화 파일 없음: {movie_file}"))
