import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.books.models import Book


class Command(BaseCommand):
    
    help = "Aladin TTB API를 사용하여 도서 데이터 수집"

    def handle(self, *args, **options):
        ttb_key = getattr(settings, 'ALADIN_TTB_KEY', None)
        if not ttb_key:
            self.stdout.write(self.style.ERROR("ALADIN_TTB_KEY가 settings에 설정되지 않았습니다."))
            return

        url = "http://www.aladin.co.kr/ttb/api/ItemList.aspx"
        params = {
            'ttbkey': ttb_key,
            'QueryType': 'BestSeller',
            'MaxResults': 50,
            'start': 2,     # 새로운 도서 수집 시 값 변경
            'SearchTarget': 'Book',
            'CategoryId': '1',  # 소설 / 시 / 희곡 카테고리
            'output': 'js',
            'Version': '20131101',
            'OptResult': 'description'
        }

        try:
            response = requests.get(url, params=params)
            items = response.json().get('item', [])
            saved_count = 0

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
                    }
                )
                if created:
                    saved_count += 1
            self.stdout.write(self.style.SUCCESS(f"도서 수집 완료 ({saved_count}개 저장)"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류: {e}"))
