import json
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.music_movie.models import Music, Movie
from daybydaybackend.books.models import Book  # 책 모델 임포트
import os
from django.db import transaction


# 외부 임포트 경로 꼬임(ModuleNotFoundError) 방지를 위해 변환 연산식을 내부에 로컬 탑재
def convert_tag_vector_to_russell(tag_vector):
    valence = (
        tag_vector.get('joy', 0) * 1.0 +
        tag_vector.get('romance', 0) * 0.7 +
        tag_vector.get('calmness', 0) * 0.4 +
        tag_vector.get('sadness', 0) * -1.0 +
        tag_vector.get('anger', 0) * -0.8 +
        tag_vector.get('fear', 0) * -0.7 +
        tag_vector.get('darkness', 0) * -0.6
    )

    arousal = (
        tag_vector.get('energy', 0) * 1.0 +
        tag_vector.get('anger', 0) * 0.7 +
        tag_vector.get('fear', 0) * 0.6 +
        tag_vector.get('dreaminess', 0) * -0.2 +
        tag_vector.get('calmness', 0) * -0.7
    )

    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))

    return valence, arousal


class Command(BaseCommand):
    help = "JSON 파일에서 음악, 영화 및 책 데이터 로드"

    def handle(self, *args, **options):
        # 1. 음악 & 영화 파일 경로 (daybydaybackend/music_movie/recommend_music_movie/)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        package_dir = os.path.join(base_dir, 'recommend_music_movie')
        music_file = os.path.join(package_dir, 'music_database.json')
        movie_file = os.path.join(package_dir, 'movie_database.json')

        # 2. 책 파일 경로 (프로젝트 루트 디렉토리 /books_data.json)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        book_file = os.path.join(root_dir, 'books_data.json')

        # === 음악 데이터 로드 ===
        if os.path.exists(music_file):
            self.stdout.write("음악 데이터 로드 중...")
            try:
                with open(music_file, 'r', encoding='utf-8') as f:
                    music_data = json.load(f)
                
                # 기존 음악 데이터 삭제 (중복 생성 방지 및 깨끗한 적재)
                self.stdout.write("기존 음악 데이터를 정리하고 새로 적재합니다...")
                Music.objects.all().delete()
                
                music_count = 0
                
                with transaction.atomic():
                    for item in music_data:
                        if item.get('type') == 'music':
                            emotion_vector = item.get('emotion_vector', {})
                            valence, arousal = convert_tag_vector_to_russell(emotion_vector)
                            
                            Music.objects.create(
                                title=item.get('title'),
                                artist=item.get('artist', ''),
                                source_tag=item.get('source_tag', ''),
                                listeners=item.get('listeners', 0),
                                playcount=item.get('playcount', 0),
                                tags=item.get('tags', []),
                                image_url=item.get('image_url', ''),  # 자켓 이미지 바인딩 반영
                                joy=emotion_vector.get('joy', 0.0),
                                sadness=emotion_vector.get('sadness', 0.0),
                                anger=emotion_vector.get('anger', 0.0),
                                fear=emotion_vector.get('fear', 0.0),
                                trust=emotion_vector.get('trust', 0.0),
                                surprise=emotion_vector.get('surprise', 0.0),
                                valence=valence,
                                arousal=arousal,
                            )
                            music_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"✓ {music_count}개의 음악 로드 완료!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"음악 로드 오류: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ 음악 파일 없음: {music_file}"))

        # === 영화 데이터 로드 ===
        if os.path.exists(movie_file):
            self.stdout.write("영화 데이터 로드 중...")
            try:
                with open(movie_file, 'r', encoding='utf-8') as f:
                    movie_data = json.load(f)
                
                # 기존 영화 데이터 정리
                self.stdout.write("기존 영화 데이터를 정리하고 새로 적재합니다...")
                Movie.objects.all().delete()
                
                movie_count = 0
                
                with transaction.atomic():
                    for item in movie_data:
                        if item.get('type') == 'movie':
                            emotion_vector = item.get('emotion_vector', {})
                            valence, arousal = convert_tag_vector_to_russell(emotion_vector)
                            
                            # 빈 날짜 포맷 예외 처리
                            release_date = item.get('release_date')
                            if not release_date or release_date == "":
                                release_date = None
                            
                            # 영화 포스터 전체 URL을 poster_path에 원본 그대로 저장 (프론트엔드 작업 편의성)
                            poster_path = item.get('image_url', '')
                                
                            Movie.objects.create(
                                tmdb_id=item.get('id'),
                                title=item.get('title'),
                                director=item.get('director', ''),
                                genre=item.get('genre', ''),
                                overview=item.get('overview', ''),
                                vote_average=item.get('vote_average'),
                                vote_count=item.get('vote_count', 0),
                                popularity=item.get('popularity', 0.0),
                                release_date=release_date,
                                poster_path=poster_path,
                                joy=emotion_vector.get('joy', 0.0),
                                sadness=emotion_vector.get('sadness', 0.0),
                                anger=emotion_vector.get('anger', 0.0),
                                fear=emotion_vector.get('fear', 0.0),
                                trust=emotion_vector.get('trust', 0.0),
                                surprise=emotion_vector.get('surprise', 0.0),
                                valence=valence,
                                arousal=arousal,
                            )
                            movie_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"✓ {movie_count}개의 영화 로드 완료!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"영화 로드 오류: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ 영화 파일 없음: {movie_file}"))

        # === 책 데이터 로드 ===
        if os.path.exists(book_file):
            self.stdout.write("책 데이터 로드 중...")
            try:
                # UTF-16LE 등 특수 인코딩 디코딩 예외 폴백 처리
                try:
                    with open(book_file, 'r', encoding='utf-8') as f:
                        book_data = json.load(f)
                except UnicodeDecodeError:
                    self.stdout.write("⚠️ UTF-8 디코딩 실패. UTF-16 인코딩으로 전환하여 재시도합니다...")
                    with open(book_file, 'r', encoding='utf-16') as f:
                        book_data = json.load(f)
                
                # 기존 도서 데이터 정리
                self.stdout.write("기존 책 데이터를 정리하고 새로 적재합니다...")
                Book.objects.all().delete()
                
                book_count = 0
                
                with transaction.atomic():
                    for item in book_data:
                        # [장고 Fixture 픽스처 규격 유연 분석 가드]
                        if 'fields' in item and 'pk' in item:
                            isbn = item['pk']
                            fields = item['fields']
                        else:
                            isbn = item.get('isbn') or item.get('isbn13')
                            fields = item
                            
                        # isbn 유무 안전 점검
                        if not isbn:
                            continue
                            
                        Book.objects.create(
                            isbn=str(isbn).strip(),
                            title=fields.get('title'),
                            author=fields.get('author', ''),
                            category=fields.get('category', fields.get('categoryName', '')),
                            description=fields.get('description', ''),
                            link=fields.get('link', ''),
                            is_review_crawled=fields.get('is_review_crawled', False),
                            cover_url=fields.get('cover_url', ''),
                            valence=fields.get('valence', 0.0),
                            arousal=fields.get('arousal', 0.0),
                            joy=fields.get('joy', 0.0),
                            sadness=fields.get('sadness', 0.0),
                            anger=fields.get('anger', 0.0),
                            fear=fields.get('fear', 0.0),
                            trust=fields.get('trust', 0.0),
                            surprise=fields.get('surprise', 0.0),
                        )
                        book_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"✓ {book_count}개의 도서 로드 완료!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"도서 로드 오류: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ 책 파일 없음: {book_file}"))
