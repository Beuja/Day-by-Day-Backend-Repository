import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.books.models import Book
from django.db.models import Q

class Command(BaseCommand):
    help = "기존 DB에 있는 도서 중 표지 이미지가 없는 도서의 Cover URL 업데이트"

    def handle(self, *args, **options):
        ttb_key = getattr(settings, 'ALADIN_TTB_KEY', None)
        if not ttb_key:
            self.stdout.write(self.style.ERROR("ALADIN_TTB_KEY가 settings에 설정되지 않았습니다."))
            return

        # cover_url이 없거나 비어있는 책들만 조회
        books_to_update = Book.objects.filter(Q(cover_url__isnull=True) | Q(cover_url__exact=''))
        total_count = books_to_update.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("업데이트할 도서가 없습니다. (모든 도서에 표지가 있습니다)"))
            return

        self.stdout.write(f"총 {total_count}개의 도서 표지 업데이트를 시작합니다...")

        # 알라딘 상품 조회(ItemLookUp) API 엔드포인트
        url = "http://www.aladin.co.kr/ttb/api/ItemLookUp.aspx"
        updated_count = 0

        for book in books_to_update:
            params = {
                'ttbkey': ttb_key,
                'itemIdType': 'ISBN13' if len(book.isbn) == 13 else 'ISBN', # ISBN 길이에 따라 타입 지정
                'ItemId': book.isbn,
                'output': 'js',
                'Version': '20131101',
                'Cover': 'Big'  # 큰 사이즈 이미지 요청
            }

            try:
                response = requests.get(url, params=params)
                data = response.json()
                items = data.get('item', [])

                if items:
                    cover_url = items[0].get('cover')
                    if cover_url:
                        book.cover_url = cover_url
                        book.save(update_fields=['cover_url']) # DB 최적화를 위해 특정 필드만 저장
                        updated_count += 1
                        self.stdout.write(f"업데이트 완료: {book.title}")
                else:
                    self.stdout.write(self.style.WARNING(f"알라딘 API 검색 실패 (단종 또는 정보 없음): {book.title} ({book.isbn})"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"API 요청 중 오류 발생 ({book.title}): {e}"))

            # 알라딘 API 호출 제한(Rate Limit)을 피하기 위해 아주 짧은 대기 시간 추가
            time.sleep(0.1) 

        self.stdout.write(self.style.SUCCESS(f"작업 완료! (총 {updated_count}개 업데이트됨)"))