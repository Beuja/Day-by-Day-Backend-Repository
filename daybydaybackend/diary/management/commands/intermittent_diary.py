import os
import json
import random
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

# 콘텐츠 모델 및 DailyRecommended 제거, 일기와 감정 모델만 남김
from daybydaybackend.diary.models import Diary, DiaryEmotion
from daybydaybackend.diary.services import analyze_emotion_hybrid

class Command(BaseCommand):
    help = "지난 기간 동안의 테스트용 일기 및 감정 데이터를 일괄 적재합니다."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='testuser', help='대상 유저명')
        parser.add_argument('--days', type=int, default=30, help='자동 생성 시 적재할 과거 일수')
        parser.add_argument('--clear', action='store_true', help='적재 전 기존 유저의 일기 및 감정 데이터를 전체 삭제')
        parser.add_argument('--manual', action='store_true', help='수동 모드로 일기 작성')
        parser.add_argument('--preset', action='store_true', help='최근 6일 시나리오 일기 프리셋 적재')
        parser.add_argument('--date', type=str, help='수동 생성 시 일기 날짜 (YYYY-MM-DD 형식)')
        parser.add_argument('--content', type=str, help='수동 생성 시 일기 내용')
        parser.add_argument('--weather', type=str, help='수동 생성 시 날씨 (SUNNY, CLOUDY, RAINY, SNOWY, WINDY, THUNDER)')

    def handle(self, *args, **options):
        username = options['username']
        days = options['days']
        clear_existing = options['clear']
        manual_mode = options['manual']
        preset_mode = options['preset']

        # 유저 검색 혹은 자동 생성
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password("pass1234!")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✔️ 임시 테스트 유저 생성 완료: {username}"))

        if clear_existing:
            # 중복 방지를 위해 기존 일기를 청소 (Cascade 옵션에 의해 감정도 자동 청소됨)
            Diary.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING(f"🧹 기존 {username} 유저의 일기 및 감정 데이터 전체 삭제 완료."))

        # 0. 프리셋 생성 모드 처리 (최근 6일에 6대 감정 시나리오 일기 순차 적재)
        if preset_mode:
            preset_templates = [
                {
                    "offset": 6,
                    "content": "오늘 면접 합격 소식을 들었다. 부모님께 전화로 알리는데 목소리가 떨려서 웃음이 났다.",
                    "weather": "SUNNY",
                    "joy": 0.9, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "trust": 0.6, "surprise": 0.3,
                    "valence": 0.8, "arousal": 0.5, "primary_emotion": "기쁨"
                },
                {
                    "offset": 5,
                    "content": "키우던 화분이 결국 시들어버렸다. 매일 들여다봤는데도 살리지 못해서 마음이 무겁다.",
                    "weather": "RAINY",
                    "joy": 0.0, "sadness": 0.85, "anger": 0.1, "fear": 0.2, "trust": 0.1, "surprise": 0.0,
                    "valence": -0.7, "arousal": -0.3, "primary_emotion": "슬픔"
                },
                {
                    "offset": 4,
                    "content": "약속 시간에 한 시간이나 늦게 나타난 친구가 사과도 없이 메뉴판부터 들었다. 화를 참느라 음식 맛이 하나도 느껴지지 않았다.",
                    "weather": "CLOUDY",
                    "joy": 0.0, "sadness": 0.1, "anger": 0.9, "fear": 0.1, "trust": 0.0, "surprise": 0.2,
                    "valence": -0.8, "arousal": 0.7, "primary_emotion": "분노"
                },
                {
                    "offset": 3,
                    "content": "창문을 열고 따뜻한 차를 마시며 책을 읽었다. 오랜만에 아무 생각 없이 보낸 오후였다.",
                    "weather": "SUNNY",
                    "joy": 0.4, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "trust": 0.85, "surprise": 0.0,
                    "valence": 0.7, "arousal": -0.4, "primary_emotion": "신뢰"
                },
                {
                    "offset": 2,
                    "content": "내일 발표 자료를 몇 번이나 다시 확인했는데도 마음이 놓이지 않는다. 잠자리에 누워도 자꾸 슬라이드가 머릿속에 떠오른다.",
                    "weather": "CLOUDY",
                    "joy": 0.0, "sadness": 0.2, "anger": 0.0, "fear": 0.8, "trust": 0.1, "surprise": 0.1,
                    "valence": -0.6, "arousal": 0.4, "primary_emotion": "두려움"
                },
                {
                    "offset": 1,
                    "content": "다음 주에 떠날 여행 일정을 정리하다 보니 시간이 훌쩍 지나갔다. 캐리어를 미리 꺼내놓고 보니 벌써 떠난 기분이 든다.",
                    "weather": "SUNNY",
                    "joy": 0.7, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "trust": 0.5, "surprise": 0.8,
                    "valence": 0.6, "arousal": 0.5, "primary_emotion": "놀람"
                }
            ]

            success_count = 0
            now = timezone.now()
            with transaction.atomic():
                for temp in preset_templates:
                    past_date = now - datetime.timedelta(days=temp["offset"])
                    past_date_only = past_date.date()
                    
                    if not clear_existing:
                        if Diary.objects.filter(user=user, created_at__date=past_date_only).exists():
                            self.stdout.write(self.style.WARNING(f"⏭️ {past_date_only} 날짜에 이미 일기가 존재하여 건너뜁니다."))
                            continue
                            
                    diary = Diary.objects.create(
                        user=user,
                        content=temp["content"],
                        weather=temp["weather"]
                    )
                    Diary.objects.filter(id=diary.id).update(created_at=past_date)
                    
                    DiaryEmotion.objects.create(
                        diary=diary,
                        joy=temp["joy"],
                        sadness=temp["sadness"],
                        anger=temp["anger"],
                        fear=temp["fear"],
                        trust=temp["trust"],
                        surprise=temp["surprise"],
                        valence=temp["valence"],
                        arousal=temp["arousal"],
                        primary_emotion=temp["primary_emotion"]
                    )
                    success_count += 1
                    
            self.stdout.write(self.style.SUCCESS(
                f"🎉 성공: '{username}' 유저에게 최근 6일 시나리오 프리셋 일기 "
                f"총 {success_count}개를 적재 완료하였습니다!"
            ))
            return

        # 0. 수동 생성 모드 처리
        if manual_mode:
            content = options['content']
            date_str = options['date']
            weather = options['weather']

            # 인자가 부족할 경우 대화식(interactive) 입력 유도
            if not date_str:
                date_str = input("일기 날짜 (YYYY-MM-DD 형식, 엔터 입력 시 오늘): ").strip()
                if not date_str:
                    date_str = timezone.now().strftime("%Y-%m-%d")
            
            try:
                past_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                self.stdout.write(self.style.ERROR("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해 주세요."))
                return

            if not content:
                content = input("일기 내용: ").strip()
                if not content:
                    self.stdout.write(self.style.ERROR("❌ 일기 내용은 비어있을 수 없습니다."))
                    return

            if not weather:
                weather = input("날씨 (SUNNY, CLOUDY, RAINY, SNOWY, WINDY, THUNDER 중 입력, 엔터 시 없음): ").strip().upper()
                if weather not in ['SUNNY', 'CLOUDY', 'RAINY', 'SNOWY', 'WINDY', 'THUNDER', '']:
                    self.stdout.write(self.style.WARNING("⚠️ 올바르지 않은 날씨 선택입니다. 날씨 없이 생성합니다."))
                    weather = None
                elif weather == '':
                    weather = None

            # 중복 체크
            past_date_only = past_date.date()
            if Diary.objects.filter(user=user, created_at__date=past_date_only).exists():
                self.stdout.write(self.style.ERROR(f"❌ {past_date_only} 날짜에 이미 일기가 존재합니다."))
                return

            with transaction.atomic():
                diary = Diary.objects.create(
                    user=user,
                    content=content,
                    weather=weather
                )
                Diary.objects.filter(id=diary.id).update(created_at=past_date)
                
                # 감정 분석 자동 연동
                emotion_dict = analyze_emotion_hybrid(content)
                DiaryEmotion.objects.create(
                    diary=diary,
                    joy=emotion_dict.get('joy', 0.0),
                    sadness=emotion_dict.get('sadness', 0.0),
                    anger=emotion_dict.get('anger', 0.0),
                    fear=emotion_dict.get('fear', 0.0),
                    trust=emotion_dict.get('trust', 0.0),
                    surprise=emotion_dict.get('surprise', 0.0),
                    valence=emotion_dict.get('valence', 0.0),
                    arousal=emotion_dict.get('arousal', 0.0),
                    primary_emotion=emotion_dict.get('primary_emotion', '알수없음')
                )
            
            self.stdout.write(self.style.SUCCESS(f"🎉 성공: '{username}' 유저의 {past_date_only} 날짜 일기 및 감정 데이터를 수동 등록하였습니다!"))
            return

        # 1. diary_data.json 파일 경로 확인 및 로딩
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_file_path = os.path.join(base_dir, 'data', 'diary_data.json')
        
        templates = []
        if os.path.exists(json_file_path):
            self.stdout.write(f"📂 외부 일기 데이터 로딩 중: {json_file_path}")
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                self.stdout.write(self.style.SUCCESS(f"✓ {len(templates)}개의 고해상도 일기 시나리오 템플릿 로딩 성공!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ JSON 파싱 실패 ({e}). 기본 내장 템플릿으로 대체합니다."))
        
        # fallback용 기본 내장 템플릿
        if not templates:
            templates = [
                {
                    "content": "오늘 오랜만에 날씨가 화창해서 친구들과 공원에서 피크닉을 즐겼다. 맛있는 도시락과 끊이지 않는 수다 속에서 더없이 기쁘고 소중한 기운을 느낀 멋진 날이었다.",
                    "weather": "SUNNY",
                    "joy": 0.85, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "trust": 0.5, "surprise": 0.2,
                    "valence": 0.8, "arousal": 0.4, "primary_emotion": "기쁨"
                },
                {
                    "content": "하늘에서 슬픈 눈물이 흐르듯 비가 하루 종일 처량하게 내렸다. 마음 한구석이 텅 빈 것처럼 울적해지고 쓸쓸한 바람 소리마저 가슴을 시리게 파고드는 우울한 하루였다.",
                    "weather": "RAINY",
                    "joy": 0.0, "sadness": 0.9, "anger": 0.1, "fear": 0.2, "trust": 0.1, "surprise": 0.0,
                    "valence": -0.7, "arousal": -0.4, "primary_emotion": "슬픔"
                },
                {
                    "content": "오래 준비해온 발표가 억울한 오해와 상대방의 무성의한 태도로 무산되었다. 속에서 끓어오르는 답답함과 화가 가라앉지 않아 머리가 핑 돌 만큼 분노가 치밀어 오른 날이다.",
                    "weather": "CLOUDY",
                    "joy": 0.0, "sadness": 0.2, "anger": 0.95, "fear": 0.1, "trust": 0.0, "surprise": 0.1,
                    "valence": -0.8, "arousal": 0.6, "primary_emotion": "분노"
                },
                {
                    "content": "중요한 시험을 앞두고 막막한 불안감이 밀려왔다. 혹시라도 실수할까 봐 걱정되고 밤이 깊어갈수록 어두운 방에서 숨이 턱턱 막히는 것 같은 초조하고 두려운 감정뿐이었다.",
                    "weather": "WINDY",
                    "joy": 0.0, "sadness": 0.3, "anger": 0.0, "fear": 0.85, "trust": 0.2, "surprise": 0.1,
                    "valence": -0.6, "arousal": 0.5, "primary_emotion": "두려움"
                },
                {
                    "content": "가장 믿고 의지하는 친한 동료들과 늦게까지 커피를 마시며 진솔한 속마음을 공유했다. 든든하게 나를 지탱해주는 굳건한 신뢰와 믿음 속에서 깊은 안도감이 차오른 평온한 날이다.",
                    "weather": "SUNNY",
                    "joy": 0.4, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "trust": 0.9, "surprise": 0.0,
                    "valence": 0.6, "arousal": -0.2, "primary_emotion": "신뢰"
                },
                {
                    "content": "전혀 생각지도 못했던 깜짝 서프라이즈 선물과 꽃다발을 받았다! 눈이 동그래질 만큼 깜짝 놀랐지만 마음이 짜릿해질 정도로 톡 쏘는 기분 좋은 충격에 휩싸인 특별한 날이다.",
                    "weather": "THUNDER",
                    "joy": 0.6, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "trust": 0.4, "surprise": 0.85,
                    "valence": 0.5, "arousal": 0.6, "primary_emotion": "놀람"
                },
                {
                    "content": "특별히 기쁘거나 슬픈 일 없이 집에서 조용히 밀린 다큐멘터리를 시청하고 따뜻한 유자차 한 잔을 마셨다. 물처럼 고요하고 잔잔하게 흘러간 잔잔한 휴식의 날이었다.",
                    "weather": "CLOUDY",
                    "joy": 0.1, "sadness": 0.1, "anger": 0.0, "fear": 0.0, "trust": 0.2, "surprise": 0.0,
                    "valence": 0.1, "arousal": -0.3, "primary_emotion": "알수없음"
                }
            ]

        now = timezone.now()
        success_count = 0

        self.stdout.write("⚙️ 일기 데이터 생성 프로세스 기동...")

        # 1. '오늘(0일 전)'은 반드시 포함하도록 set 초기화
        past_days = {0}
        
        # 2. 전체 기간(days)의 약 절반 정도만 무작위로 날짜를 뽑아냄
        num_diaries_to_create = max(1, days // 2)
        if days > 1:
            # 1일부터 days-1일 사이에서 랜덤 추출
            random_days = random.sample(range(1, days), num_diaries_to_create - 1)
            past_days.update(random_days)
            
        # 3. 과거 날짜부터 순차적으로 DB에 들어가도록 내림차순 정렬
        sorted_past_days = sorted(list(past_days), reverse=True)

        with transaction.atomic():
            for i in sorted_past_days:
                past_date = now - datetime.timedelta(days=i)
                past_date_only = past_date.date()
                
                # --clear가 지정되지 않은 경우, 해당 날짜에 이미 일기가 존재하면 중복 작성을 방지하기 위해 건너뜀
                if not clear_existing:
                    if Diary.objects.filter(user=user, created_at__date=past_date_only).exists():
                        self.stdout.write(self.style.WARNING(f"⏭️ {past_date_only} 날짜에 이미 일기가 존재하여 건너뜁니다."))
                        continue
                
                temp = templates[success_count % len(templates)]
                
                # 1. 일기 레코드 생성
                diary = Diary.objects.create(
                    user=user,
                    content=temp["content"],
                    weather=temp["weather"]
                )
                
                # auto_now_add 가드를 우회하여 DB 과거 일자 강제 갱신 이식
                Diary.objects.filter(id=diary.id).update(created_at=past_date)
                
                # 2. 감정 레코드 생성
                DiaryEmotion.objects.create(
                    diary=diary,
                    joy=temp["joy"],
                    sadness=temp["sadness"],
                    anger=temp["anger"],
                    fear=temp["fear"],
                    trust=temp["trust"],
                    surprise=temp["surprise"],
                    valence=temp["valence"],
                    arousal=temp["arousal"],
                    primary_emotion=temp["primary_emotion"]
                )
                
                success_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"🎉 성공: '{username}' 유저에게 {days}일 동안 불규칙한 간격으로 작성된 "
            f"총 {success_count}개의 일기 및 감정 데이터셋을 적재 완료하였습니다!"
        ))