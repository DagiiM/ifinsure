"""
Management command to create wallets for existing users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.wallets.models import Wallet

User = get_user_model()


class Command(BaseCommand):
    help = 'Create wallets for all users who do not have one'
    
    def handle(self, *args, **options):
        users_without_wallet = User.objects.filter(wallet__isnull=True)
        count = 0
        
        for user in users_without_wallet:
            Wallet.objects.create(user=user)
            count += 1
            self.stdout.write(f'Created wallet for: {user.email}')
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All users already have wallets!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created {count} wallet(s)'))
