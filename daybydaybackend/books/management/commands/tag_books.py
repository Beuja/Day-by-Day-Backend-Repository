# books/management/commands/tag_books.py
# LLM API를 활용해 책 태깅
import google.genai as genai    
from google.genai import types
import json
import time
import os
import re
# Playwright의 내부 이벤트 루프와 Django ORM의 충돌을 방지하는 환경 변수 설정
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from playwright.sync_api import sync_playwright
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.books.models import Book


class Command(BaseCommand):
    help = "리뷰 크롤링 후 Gemini API를 사용하여 도서의 감정 벡터 태깅"

    def crawl_reviews(self, page, book_url):
        reviews = []
        try:
            match = re.search(r'ItemId=(\d+)', book_url, re.IGNORECASE)
            if not match:
                self.stdout.write(self.style.WARNING("    -> URL에서 ItemId를 찾을 수 없습니다."))
                return reviews

            item_id = match.group(1)

            ajax_url = (
                f"https://www.aladin.co.kr/ucl/shop/product/ajax/GetCommunityListAjax.aspx?"
                f"ProductItemId={item_id}&itemId={item_id}&pageCount=20&communitytype=CommentReview"
                f"&nemoType=-1&page=1&startNumber=1&endNumber=20&sort=2&IsOrderer=1&BranchType=1"
                f"&IsAjax=true&pageType=0"
            )

            page.goto(ajax_url, referer=book_url, timeout=15000)
            page.wait_for_timeout(1500)
            
            body_text = page.inner_text("body")
            body_text = re.sub(r'\s+', ' ', body_text).strip()

            raw_reviews = body_text.split("Thanks to 공감")

            for text in raw_reviews:
                clean_text = re.sub(r'\S+\s+\d{4}-\d{2}-\d{2}\s*공감\s*\(\d+\)\s*댓글\s*\(\d+\)', '', text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                if len(clean_text) > 5 and clean_text not in reviews:
                    reviews.append(clean_text)

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    -> 크롤링 실패: {e}"))
        return reviews

    def extract_emotion_vector(self, reviews_list):
        if not reviews_list:
            return None, None
            
        # 리뷰가 20개 정도만 사용
        combined_text = "\n".join(reviews_list[:20])
        
        prompt = f"""
        다음은 특정 도서에 대한 독자들의 리뷰이며 학술적 분석을 위한 데이터가 필요합니다:
        {combined_text}
        
        이 리뷰들을 종합하여, 이 책이 독자에게 주는 감정을 러셀의 감정 모델에 따라 분석해 주세요.
        - valence (정서가): -1.0(매우 불쾌/슬픔) ~ 1.0(매우 쾌/기쁨)
        - arousal (각성도): -1.0(매우 차분/지루함) ~ 1.0(매우 격앙/흥분)
        
        반드시 아래 JSON 형식으로만 답변해 주세요. 다른 설명은 생략합니다.
        {{"valence": 0.5, "arousal": -0.2}}
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                api_key = getattr(settings, 'GEMINI_API_KEY', None)
                client = genai.Client(api_key=api_key)

                """
                for model in client.models.list():
                    self.stdout.write(f"모델 이름: {model.name}")
                """
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                

                result_str = response.text.strip()
                
                result_str = re.sub(r'^```(json)?\s*', '', result_str)
                result_str = re.sub(r'\s*```$', '', result_str)

                data = json.loads(result_str)    
                valence = max(-1.0, min(1.0, float(data.get('valence', 0.0))))
                arousal = max(-1.0, min(1.0, float(data.get('arousal', 0.0))))
                
                return valence, arousal
                
            except Exception as e:
                error_msg = str(e)
                # 429 에러(할당량 초과)인 경우 처리
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if attempt < max_retries - 1:
                        self.stdout.write(self.style.WARNING(f"    -> API 한도 초과. 30초 대기 후 재시도합니다... ({attempt+1}/{max_retries})"))
                        time.sleep(30) # 30초 쿨타임
                        continue
                            
                # 429 에러가 아니거나, 재시도 횟수를 다 채웠을 경우
                self.stdout.write(self.style.ERROR(f"    -> 감정 추출 실패: {e}"))
                return None, None
            
    def update_book_emotion(self, book, valence, arousal):
        book.valence = valence
        book.arousal = arousal
        book.is_review_crawled = True
        book.save()

    def handle(self, *args, **options):
        target_books = Book.objects.filter(link__isnull=False, valence__isnull=True)[:20]

        if not target_books:
            self.stdout.write(self.style.SUCCESS("태깅이 필요한 도서가 없습니다."))
            return
        
        user_agent_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"]
            )
            context = browser.new_context(user_agent=user_agent_str)
            page = context.new_page()

            for book in target_books:
                self.stdout.write(f"태깅 시도: {book.title}")

                if not browser.is_connected():
                    browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"])
                    context = browser.new_context(user_agent=user_agent_str)
                    page = context.new_page()
                elif page.is_closed():
                    page = context.new_page()

                try:
                    context.clear_cookies()
                    crawled_reviews = self.crawl_reviews(page, book.link)
                    review_count = len(crawled_reviews)
                    
                    if(review_count > 0):
                        self.stdout.write(self.style.SUCCESS(f"    -> 리뷰 {review_count}개 크롤링 완료"))

                        if(review_count < 3):
                            self.stdout.write(self.style.WARNING("    -> 리뷰 수가 충분하지 않아 0,0으로 설정합니다"))
                            self.update_book_emotion(book, 0.0, 0.0)

                        else:
                            """
                            self.stdout.write("    [수집된 리뷰 미리보기]")
                            for idx, review_text in enumerate(crawled_reviews, 1):
                                # 너무 길면 터미널 창이 복잡해지므로 앞의 50글자만 잘라서 보여줍니다.
                                preview = review_text[:50] + "..." if len(review_text) > 50 else review_text
                                self.stdout.write(f"      {idx}. {preview}")
                            self.stdout.write("    ------------------------")
                            """
                            valence, arousal = self.extract_emotion_vector(crawled_reviews)

                            if valence is not None and arousal is not None:
                                self.update_book_emotion(book, valence, arousal)
                                self.stdout.write(self.style.SUCCESS(f"    -> 태깅 완료 (valence: {valence}, arousal: {arousal})"))
                            else:
                                self.stdout.write(self.style.WARNING("    -> 감정 벡터 추출 실패"))

                    else:
                        self.stdout.write(self.style.WARNING("    -> 수집된 리뷰 없음"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    -> 루프 내부 처리 중 에러 발생: {e}"))

                time.sleep(4)
            browser.close()