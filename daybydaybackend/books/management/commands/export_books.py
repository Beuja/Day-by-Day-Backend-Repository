import json
import os
from django.core.management.base import BaseCommand
from daybydaybackend.books.models import Book

class Command(BaseCommand):
    help = "DB의 도서 데이터를 알라딘 수집기 호환 커스텀 JSON 포맷으로 내보냅니다."

    def handle(self, *args, **options):
        # 최상위 루트 디렉토리 및 저장할 파일 경로 설정
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        json_file = os.path.join(root_dir, 'books_data.json')

        books = Book.objects.all()
        book_data_list = []

        for book in books:
            # 원하시는 규격 그대로 딕셔너리 구조 생성
            entry = {
                "fields": {
                    "isbn": book.isbn,
                    "title": book.title,
                    "author": book.author,
                    "category": book.category,
                    "description": book.description,
                    "link": book.link,
                    "cover_url": book.cover_url,
                    "is_review_crawled": book.is_review_crawled,
                    "valence": book.valence,
                    "arousal": book.arousal,
                    "joy": book.joy,
                    "sadness": book.sadness,
                    "anger": book.anger,
                    "fear": book.fear,
                    "trust": book.trust,
                    "surprise": book.surprise
                }
            }
            book_data_list.append(entry)

        # JSON 파일로 저장
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(book_data_list, f, ensure_ascii=False, indent=4)

        self.stdout.write(self.style.SUCCESS(f"성공: {len(book_data_list)}개의 도서를 커스텀 포맷으로 내보냈습니다. ({json_file})"))