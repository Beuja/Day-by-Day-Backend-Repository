from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """유저가 회원가입(Create)될 때 프로필을 자동으로 생성"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """유저 정보가 저장될 때 프로필도 함께 저장되도록 보장"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()