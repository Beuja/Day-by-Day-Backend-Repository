from django.db.backends.signals import connection_created
from django.dispatch import receiver

@receiver(connection_created)
def configure_sqlite(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        # WAL 모드 활성화 (읽기와 쓰기 세션이 락 충돌 없이 대폭 개선됨)
        cursor.execute('PRAGMA journal_mode=WAL;')
        # I/O 동기화 대기를 정상 수준으로 완화
        cursor.execute('PRAGMA synchronous=NORMAL;')
