import json
import os
import re
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from playwright.sync_api import sync_playwright
from daybydaybackend.diary.services import analyze_emotion_hybrid

# Playwright의 내부 이벤트 루프와 Django ORM의 충돌을 방지하는 환경 변수 설정
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class Command(BaseCommand):
    help = "Playwright로 알라딘 리뷰를 크롤링하고, diary 앱의 EmotionAnalyzer를 사용해 감정을 분석하여 원본 books_data.json에 직접 업데이트"

    def crawl_reviews(self, page, book_url):
        reviews = []
        try:
            match = re.search(r'ItemId=(\d+)', book_url, re.IGNORECASE)
            if not match:
                self.stdout.write(self.style.WARNING("    -> URL에서 ItemId를 찾을 수 없습니다."))
                return reviews

            item_id = match.group(1)
            target_total_count = 50     # 최대 리뷰 50개

            for p in [1, 2, 3]:
                ajax_url = (
                    f"https://www.aladin.co.kr/ucl/shop/product/ajax/GetCommunityListAjax.aspx?"
                    f"ProductItemId={item_id}&itemId={item_id}&pageCount=20&communitytype=CommentReview"
                    f"&nemoType=-1&page={p}&startNumber=1&endNumber=20&sort=2&IsOrderer=1&BranchType=1"
                    f"&IsAjax=true&pageType=0"
                )

                page.goto(ajax_url, referer=book_url, timeout=15000)
                page.wait_for_timeout(1500)
                
                body_text = page.inner_text("body")
                body_text = re.sub(r'\s+', ' ', body_text).strip()

                raw_reviews = body_text.split("Thanks to 공감")

                has_new_reviews = False
                
                for text in raw_reviews:
                    clean_text = re.sub(r'\S+\s+\d{4}-\d{2}-\d{2}\s*공감\s*\(\d+\)\s*댓글\s*\(\d+\)', '', text)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    if len(clean_text) > 5 and clean_text not in reviews:
                        reviews.append(clean_text)
                        has_new_reviews = True

                        if len(reviews) >= target_total_count:
                            return reviews[:target_total_count]

                if not has_new_reviews or len(raw_reviews) <= 1:
                    break

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    -> 크롤링 실패: {e}"))
        
        return reviews[:target_total_count]

    def extract_emotion_vector_local(self, reviews_list):
        """
        [고도화 패치] 무거운 외부 Gemini API 호출 대신, 
        로컬의 diary.services.analyze_emotion_hybrid (Kiwi 형태소 + 사전)를 구동하여 
        오프라인에서 초고속으로 감정을 추출합니다.
        """
        if not reviews_list:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            
        combined_text = "\n".join(reviews_list[:50])
        try:
            res = analyze_emotion_hybrid(combined_text)
            
            joy = round(res.get('joy', 0.0), 4)
            sadness = round(res.get('sadness', 0.0), 4)
            anger = round(res.get('anger', 0.0), 4)
            fear = round(res.get('fear', 0.0), 4)
            trust = round(res.get('trust', 0.0), 4)
            surprise = round(res.get('surprise', 0.0), 4)
            valence = round(res.get('valence', 0.0), 4)
            arousal = round(res.get('arousal', 0.0), 4)
            
            return joy, sadness, anger, fear, trust, surprise, valence, arousal
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    ⚠️ 로컬 감정 분석 실패: {e}"))
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    def handle(self, *args, **options):
        # 1. 경로 정의 (원본 books_data.json에 직접 in-place 저장하도록 일치)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        input_file = os.path.join(root_dir, 'books_data.json')
        output_file = input_file

        if not os.path.exists(input_file):
            self.stdout.write(self.style.ERROR(f"❌ 입력 파일이 없습니다: {input_file}"))
            return

        self.stdout.write("📚 books_data.json 로딩 중...")
        file_encoding = 'utf-8'
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
        except UnicodeDecodeError:
            self.stdout.write("⚠️ UTF-8 디코딩 실패. UTF-16 인코딩으로 전환하여 로딩합니다...")
            file_encoding = 'utf-16'
            with open(input_file, 'r', encoding='utf-16') as f:
                book_data = json.load(f)

        # 아직 크롤링 및 태깅이 되지 않은 도서 선별 (is_review_crawled가 False인 도서 최대 10권씩 루프 처리하여 안정성 확보)
        target_items = []
        for item in book_data:
            fields = item['fields'] if 'fields' in item else item
            if fields.get('link') and not fields.get('is_review_crawled', False):
                target_items.append(item)
                if len(target_items) >= 10:  # 너무 무리하지 않게 한 번에 10권 단위 배치 크롤링
                    break

        if not target_items:
            self.stdout.write(self.style.SUCCESS("🎉 이미 모든 도서의 크롤링 및 감정 분석 태깅이 완료되었습니다!"))
            return

        self.stdout.write(f"✓ 크롤링/분석이 필요한 도서 {len(target_items)}권을 탐색했습니다. Playwright 크롤러 기동!")

        user_agent_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage", "--no-sandbox"]
            )
            context = browser.new_context(user_agent=user_agent_str)
            page = context.new_page()

            for item in target_items:
                fields = item['fields'] if 'fields' in item else item
                title = fields.get('title', '제목 없음')
                link = fields.get('link')

                self.stdout.write(f"📖 크롤링 및 분석 시도: {title}")

                if not browser.is_connected():
                    browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"])
                    context = browser.new_context(user_agent=user_agent_str)
                    page = context.new_page()
                elif page.is_closed():
                    page = context.new_page()

                try:
                    context.clear_cookies()
                    crawled_reviews = self.crawl_reviews(page, link)
                    review_count = len(crawled_reviews)
                    
                    if review_count > 0:
                        self.stdout.write(self.style.SUCCESS(f"    -> 리뷰 {review_count}개 크롤링 완료"))

                        if review_count < 10:
                            self.stdout.write(self.style.WARNING("    -> 리뷰 수가 충분하지 않아(10개 미만) 감정을 0,0 기본값으로 매핑합니다."))
                            for k in ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise', 'valence', 'arousal']:
                                fields[k] = 0.0
                            fields['is_review_crawled'] = True
                        else:
                            # [핵심 로직] 수집된 실시간 독자 리뷰 텍스트 결합 후 로컬 형태소 감정 분석 가동
                            joy, sadness, anger, fear, trust, surprise, valence, arousal = self.extract_emotion_vector_local(crawled_reviews)

                            fields['joy'] = joy
                            fields['sadness'] = sadness
                            fields['anger'] = anger
                            fields['fear'] = fear
                            fields['trust'] = trust
                            fields['surprise'] = surprise
                            fields['valence'] = valence
                            fields['arousal'] = arousal
                            fields['is_review_crawled'] = True
                            
                            self.stdout.write(self.style.SUCCESS(f"    -> 🧠 로컬 형태소 분석기 연산 완료 (valence: {valence}, joy: {joy})"))
                    else:
                        self.stdout.write(self.style.WARNING("    -> 수집된 독자 리뷰 없음 (기본값 설정)"))
                        for k in ['joy', 'sadness', 'anger', 'fear', 'trust', 'surprise', 'valence', 'arousal']:
                            fields[k] = 0.0
                        fields['is_review_crawled'] = True

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    -> 루프 내부 처리 중 에러 발생: {e}"))

                # 알라딘 서버 부하 방지 및 차단 회피를 위한 안전 지연시간
                time.sleep(4)
                
            browser.close()

        # 3. 분석 결과 원본 books_data.json에 직접 inplace 저장 진행
        self.stdout.write(f"💾 원본 books_data.json 파일에 감정 덮어쓰기 진행 중 ({file_encoding})...")
        try:
            with open(output_file, 'w', encoding=file_encoding) as f:
                json.dump(book_data, f, ensure_ascii=False, indent=4)
            self.stdout.write(self.style.SUCCESS(f"🎉 성공! {len(target_items)}권의 도서 리뷰를 로컬에서 형태소 분석하여 원본 파일에 덮어쓰기 완료했습니다!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 원본 JSON 저장 실패: {e}"))