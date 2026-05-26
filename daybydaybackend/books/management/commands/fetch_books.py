import requests
import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.books.models import Book


class Command(BaseCommand):
    
    help = "Aladin TTB API를 사용하여 도서 데이터 수집"

    def handle(self, *args, **options):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        json_file = os.path.join(root_dir, 'books_data.json')

        # 기존 books_data.json 데이터 로드
        book_data_list = []
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    book_data_list = json.load(f)
            except UnicodeDecodeError:
                with open(json_file, 'r', encoding='utf-16') as f:
                    book_data_list = json.load(f)

        existing_isbns = set()
        for item in book_data_list:
            fields = item.get('fields', item)
            if 'isbn' in fields:
                existing_isbns.add(fields['isbn'])

        ttb_key = getattr(settings, 'ALADIN_TTB_KEY', None)
        if not ttb_key:
            self.stdout.write(self.style.ERROR("ALADIN_TTB_KEY가 settings에 설정되지 않았습니다."))
            return

        url = "http://www.aladin.co.kr/ttb/api/ItemList.aspx"
        params = {
            'ttbkey': ttb_key,
            'QueryType': 'BestSeller',
            'MaxResults': 50,
            'start': 4,     # 새로운 도서 수집 시 값 변경
            'SearchTarget': 'Book',
            'CategoryId': '1',  # 소설 / 시 / 희곡 카테고리
            'output': 'js',
            'Version': '20131101',
            'OptResult': 'description'
        }

        try:
            response = requests.get(url, params=params)
            items = response.json().get('item', [])
            db_saved_count = 0
            json_added_count = 0

            for item in items:
                self.stdout.write(f"저장 시도: {item.get('title')}")
                isbn = item.get('isbn13') or item.get('isbn')
                if not isbn:
                    continue

                full_category = item.get('categoryName', '')
                # 중복 방지 저장
                book, created = Book.objects.get_or_create(
                    isbn=isbn,
                    defaults={
                        'title': item.get('title'),
                        'author': item.get('author'),
                        'category': full_category.split('>')[-1] if full_category else '기타',
                        'description': item.get('description', ''),
                        'link': item.get('link'),
                        'cover_url': item.get('cover', '')
                    }
                )
                if created:
                    db_saved_count += 1

                if isbn not in existing_isbns:
                    new_json_entry = {
                        "fields": {
                            'isbn': isbn,
                            'title': item.get('title'),
                            'author': item.get('author'),
                            'category': full_category.split('>')[-1] if full_category else '기타',
                            'description': item.get('description', ''),
                            'link': item.get('link'),
                            'cover_url': item.get('cover', '')
                        }
                    }
                    book_data_list.append(new_json_entry)
                    existing_isbns.add(isbn)
                    json_added_count += 1

            # JSON 파일 덮어쓰기
            if json_added_count > 0:
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(book_data_list, f, ensure_ascii=False, indent=4)

            self.stdout.write(self.style.SUCCESS(f"DB 저장: {db_saved_count}개, JSON 추가: {json_added_count}개"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류: {e}"))
