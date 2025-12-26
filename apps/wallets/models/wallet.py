"""
Wallet models for tracking user balances and transactions.
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid
from apps.core.models import BaseModel


class Wallet(BaseModel):
    """
    User wallet for tracking balance.
    Each user has one wallet, auto-created on registration.
    """
    CURRENCY_CHOICES = [
        ('KES', 'Kenyan Shilling'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='KES')
    
    # is_active, created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
    
    def __str__(self):
        return f"{self.user.email} - {self.currency} {self.balance}"
    
    def credit(self, amount, description='', reference=None, transaction_type='credit'):
        """Add funds to wallet."""
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        
        self.balance += Decimal(str(amount))
        self.save()
        
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference=reference
        )
    
    def debit(self, amount, description='', reference=None, transaction_type='debit'):
        """Remove funds from wallet."""
        if amount <= 0:
            raise ValueError("Debit amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        
        self.balance -= Decimal(str(amount))
        self.save()
        
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=-amount,
            balance_after=self.balance,
            description=description,
            reference=reference
        )
    
    def can_debit(self, amount):
        """Check if wallet has sufficient balance."""
        return self.balance >= Decimal(str(amount))


class WalletTransaction(BaseModel):
    """
    Transaction history for wallet.
    Provides full audit trail of all wallet movements.
    """
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('premium_payment', 'Premium Payment'),
        ('claim_payout', 'Claim Payout'),
        ('adjustment', 'Adjustment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    metadata = models.JSONField(default=dict, blank=True)
    
    # created_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f"{self.wallet.user.email}: {sign}{self.amount} ({self.transaction_type})"
    
    @property
    def is_credit(self):
        return self.amount >= 0
    
    @property
    def is_debit(self):
        return self.amount < 0
