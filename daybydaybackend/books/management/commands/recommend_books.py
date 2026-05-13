# books/management/commands/recommend_books.py
# 테스트용 추천 커맨드
import math
from daybydaybackend.books.models import Book
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "테스트용 도서 추천 명령어"

    def add_arguments(self, parser):
        parser.add_argument('--valence', type=float, default=-0.5, help='유쾌도 (-1.0 ~ 1.0)')
        parser.add_argument('--arousal', type=float, default=-0.2, help='각성도 (-1.0 ~ 1.0)')
        parser.add_argument('--mode', type=str, default='shift', help='추천 전략 (maintain/shift/amplification)')
        parser.add_argument('--count', type=int, default=3, help='추천 도서 개수')

    def handle(self, *args, **options):
        v = options['valence']
        a = options['arousal']
        mode = options['mode']
        count = options['count']

        self.stdout.write(f"테스트 값: V={v}, A={a}, Mode={mode}, Count={count}")
        
        target_v, target_a = v, a

        # shift mode
        if mode == 'shift':
            if v >= 0:
                target_v = -0.5
                target_a = -0.5
            else:
                target_v = 0.5
                target_a = 0.5
        
        # amplification mode
        if mode == 'amplification':
            target_v = v * 1.5
            target_a = a * 1.5
            target_v = max(-1.0, min(1.0, target_v))
            target_a = max(-1.0, min(1.0, target_a))

        # 모든 책과 거리 계산
        all_books = Book.objects.filter(valence__isnull=False)
        
        scored_books = []
        for book in all_books:
            distance = math.sqrt(
                (target_v - book.valence) ** 2 + (target_a - book.arousal) ** 2
            )
            scored_books.append((distance, book))

        scored_books.sort(key=lambda x: x[0])

        self.stdout.write(self.style.SUCCESS(f"\n상위 {count}개 추천 도서:"))
        for idx, (distance, book) in enumerate(scored_books[:count], 1):
            self.stdout.write(f"{idx}. {book.title} (거리: {distance:.3f})")
