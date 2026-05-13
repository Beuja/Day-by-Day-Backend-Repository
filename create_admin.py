import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User

# admin 유저 생성 (중복 방지)
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✓ admin 유저 생성 완료!")
    print("  - 아이디: admin")
    print("  - 비밀번호: admin123")
else:
    print("⚠ admin 유저가 이미 존재합니다.")
