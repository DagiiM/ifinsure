"""
Signals for wallet app - auto-create wallet on user registration.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Automatically create a wallet when a new user is registered.
    """
    if created:
        from apps.wallets.models import Wallet
        Wallet.objects.get_or_create(user=instance)
