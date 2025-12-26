"""
Payment model.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel


class Payment(BaseModel):
    """Payment records."""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('cheque', 'Cheque'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    payment_reference = models.CharField(max_length=100, unique=True, db_index=True, blank=True)
    
    # Relationships
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.PROTECT,
        related_name='payments'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_payments'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='External transaction reference'
    )
    # payment_date replaced by created_at from BaseModel
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
    
    def __str__(self):
        return f"{self.payment_reference} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = self._generate_payment_reference()
        super().save(*args, **kwargs)
    
    def _generate_payment_reference(self):
        """Generate unique payment reference."""
        prefix = f"PAY-{timezone.now().strftime('%Y%m%d')}"
        last = Payment.objects.filter(
            payment_reference__startswith=prefix
        ).order_by('-payment_reference').first()
        if last:
            seq = int(last.payment_reference.split('-')[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"
