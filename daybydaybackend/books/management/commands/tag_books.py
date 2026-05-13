# books/management/commands/tag_books.py
# LLM API를 활용해 책 태깅 (Gemini 사용)
import google.genai as genai    
from google.genai import types
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from daybydaybackend.books.models import Book


class Command(BaseCommand):
    help = "Gemini API를 사용하여 도서의 감정 벡터 태깅"

    def handle(self, *args, **options):
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY가 settings에 설정되지 않았습니다."))
            return

        client = genai.Client(api_key=api_key)
        books = Book.objects.filter(valence__isnull=True)  # 태깅되지 않은 책만 추출

        # 민감 키워드 차단 설정 해제
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
        ]

        count = 0
        for book in books:
            prompt = f"""
도서명: {book.title}
저자: {book.author}
줄거리: {book.description}

이 도서의 감정적 특성을 러셀 감정 원형 모델(Russell's Circumplex Model)을 기반으로 분석하세요.
응답은 반드시 JSON 형식으로만 반환하세요: {{"valence": 수치, "arousal": 수치}}
(valence: -1.0(불쾌) ~ 1.0(유쾌), arousal: -1.0(차분) ~ 1.0(흥분))
"""
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        safety_settings=safety_settings,
                        response_mime_type="application/json"
                    )
                )

                if not response.candidates or not response.candidates[0].content.parts:
                    reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                    self.stdout.write(f"태깅 차단됨: {book.title} (사유: {reason})")
                    continue
                
                # JSON 파싱
                text = response.text.strip().replace('```json', '').replace('```', '')
                data = json.loads(text)
                
                # 범위 확인
                valence = max(-1.0, min(1.0, float(data.get('valence', 0.0))))
                arousal = max(-1.0, min(1.0, float(data.get('arousal', 0.0))))
                
                book.valence = valence
                book.arousal = arousal
                book.save()
                
                count += 1
                self.stdout.write(f"✓ {book.title} (V:{valence:.2f}, A:{arousal:.2f})")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠ {book.title} - 오류: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"\n총 {count}권의 도서 태깅 완료!"))
