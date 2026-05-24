from django.core.management.base import BaseCommand
from daybydaybackend.books.models import Book          # 실제 앱 이름으로 수정
from daybydaybackend.books.services import recommend_books # 실제 함수가 위치한 파일 경로로 수정

class Command(BaseCommand):
    help = '6가지 기본 감정 기반 도서 추천 알고리즘을 터미널에서 테스트합니다.'

    def add_arguments(self, parser):
        # 6개의 감정 수치를 순서대로 입력받습니다.
        parser.add_argument(
            'emotions', 
            nargs=6, 
            type=float, 
            help='joy sadness anger fear trust surprise 순서로 6개 수치 입력 (예: 0.8 0.1 0.0 0.0 0.5 0.2)'
        )
        parser.add_argument(
            '--mode', 
            type=str, 
            default='maintain', 
            choices=['maintain', 'shift', 'amplification'], 
            help='추천 동작 모드 (기본값: maintain)'
        )
        parser.add_argument(
            '--count', 
            type=int, 
            default=3, 
            help='추천받을 도서 개수 (기본값: 3)'
        )

    def handle(self, *args, **options):
        # 1. 터미널 입력값 가져오기
        emotions_input = options['emotions']
        mode = options['mode']
        count = options['count']

        # 2. 함수가 dict 타입을 요구하므로, 입력받은 리스트를 dict로 변환
        emotion_keys = ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise']
        user_emotion_dict = dict(zip(emotion_keys, emotions_input))

        self.stdout.write(f"\n[테스트 조건]")
        self.stdout.write(f"감정 데이터: {user_emotion_dict}")
        self.stdout.write(f"추천 모드: {mode} / 요청 개수: {count}권\n")

        try:
            # 3. 추천 로직 실행
            recommended_books = recommend_books(
                user_emotion=user_emotion_dict, 
                mode=mode, 
                count=count
            )
            
            # 4. 결과 출력
            if not recommended_books:
                self.stdout.write(self.style.WARNING("해당 모드의 반경 조건(radius_limit)에 맞는 도서를 찾지 못했습니다."))
                return

            self.stdout.write(self.style.SUCCESS(f"✅ 총 {len(recommended_books)}권의 도서가 추천되었습니다:"))
            self.stdout.write("-" * 60)
            
            for idx, book in enumerate(recommended_books, 1):
                # Book 모델의 실제 제목 필드명('title' 등)으로 수정하세요
                title = getattr(book, 'title', f'Book ID: {book.isbn}')
                
                self.stdout.write(f"{idx}. {title}")
                self.stdout.write(
                    f"   └ [기쁨:{book.joy:.2f} 슬픔:{book.sadness:.2f} 분노:{book.anger:.2f} "
                    f"공포:{book.fear:.2f} 신뢰:{book.trust:.2f} 놀람:{book.surprise:.2f}]"
                )
            self.stdout.write("-" * 60 + "\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"실행 중 오류 발생: {e}"))