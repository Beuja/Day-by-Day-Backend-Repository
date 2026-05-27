import requests
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from daybydaybackend.books.models import Book

class Command(BaseCommand):
    help = "알라딘 API를 사용하여 도서의 누락된 cover_url을 업데이트합니다."

    def add_arguments(self, parser):
        # --all 옵션을 주면 모든 도서의 커버를 다시 업데이트합니다.
        parser.add_argument(
            '--all', 
            action='store_true', 
            help='기존에 커버 이미지가 있는 도서도 포함하여 모두 업데이트합니다.'
        )

    def handle(self, *args, **options):
        ttb_key = getattr(settings, 'ALADIN_TTB_KEY', None)
        if not ttb_key:
            self.stdout.write(self.style.ERROR("ALADIN_TTB_KEY가 settings에 설정되지 않았습니다."))
            return

        # 옵션에 따라 업데이트 대상 필터링
        update_all = options['all']
        if update_all:
            books = Book.objects.all()
            self.stdout.write("모든 도서의 커버 업데이트를 시작합니다...")
        else:
            # cover_url이 null이거나 빈 문자열인 도서만 선택
            books = Book.objects.filter(Q(cover_url__isnull=True) | Q(cover_url__exact=''))
            self.stdout.write("커버 이미지가 누락된 도서의 업데이트를 시작합니다...")

        total_books = books.count()
        self.stdout.write(f"업데이트 대상 도서: {total_books}권")

        if total_books == 0:
            return

        # 단행본 상세 조회(ItemLookUp) API 사용
        url = "http://www.aladin.co.kr/ttb/api/ItemLookUp.aspx"
        updated_count = 0
        failed_count = 0

        for book in books:
            isbn = book.isbn
            if not isbn:
                continue

            # ISBN 길이에 따라 요청 타입 결정 (알라딘 API 규격)
            item_id_type = 'ISBN13' if len(isbn) == 13 else 'ISBN'

            params = {
                'ttbkey': ttb_key,
                'itemIdType': item_id_type,
                'ItemId': isbn,
                'output': 'js',
                'Version': '20131101'
            }

            try:
                response = requests.get(url, params=params)
                data = response.json()
                items = data.get('item', [])

                if items:
                    cover_url = items[0].get('cover', '')
                    if cover_url:
                        book.cover_url = cover_url
                        # cover_url 필드만 업데이트하여 DB 부하 최소화
                        book.save(update_fields=['cover_url']) 
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"✅ 업데이트: {book.title}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"⚠️ 커버 없음: {book.title}"))
                        failed_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"❌ 검색 실패 (API 결과 없음): {book.title} (ISBN: {isbn})"))
                    failed_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"🔥 에러 발생 ({book.title}): {e}"))
                failed_count += 1

            # 알라딘 API 초당 요청 제한(Rate Limit)을 피하기 위해 0.2초 대기
            time.sleep(0.2)

        self.stdout.write(self.style.SUCCESS(f"\n작업 완료 - 성공: {updated_count}권, 실패/없음: {failed_count}권"))