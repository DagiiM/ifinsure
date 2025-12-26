"""
Payment models for processing and tracking payments.
Supports multiple payment methods including P2P with proof verification.
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid
from apps.core.models import BaseModel, SimpleBaseModel


class PaymentMethod(BaseModel):
    """
    Configurable payment methods (M-Pesa, Bank Transfer, Card, etc.)
    """
    METHOD_TYPES = [
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card Payment'),
        ('p2p', 'P2P Transfer'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('crypto', 'Cryptocurrency'),
        ('cash', 'Cash'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    # Display settings
    icon = models.CharField(max_length=100, blank=True, help_text="Icon class or URL")
    display_order = models.PositiveIntegerField(default=0)
    
    # Configuration
    # is_active provided by BaseModel
    requires_proof = models.BooleanField(
        default=False,
        help_text="Whether this method requires proof of payment (e.g., P2P)"
    )
    min_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    max_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Payment details template (JSON schema for required fields)
    payment_details_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema defining required payment details"
    )
    
    # Provider configuration
    provider_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Provider-specific configuration"
    )
    
    # Instructions for user
    instructions = models.TextField(
        blank=True,
        help_text="Instructions displayed to user when using this method"
    )
    
    # created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class PaymentAccount(BaseModel):
    """
    Company payment accounts for receiving P2P payments.
    E.g., M-Pesa number, Bank account details.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    name = models.CharField(max_length=100, help_text="Display name for this account")
    account_details = models.JSONField(
        help_text="Account details (number, name, etc.)"
    )
    # is_active provided by BaseModel
    display_order = models.PositiveIntegerField(default=0)
    
    # created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Payment Account'
        verbose_name_plural = 'Payment Accounts'
        ordering = ['display_order']
    
    def __str__(self):
        return f"{self.name} - {self.payment_method.name}"


class Payment(BaseModel):
    """
    Main payment record tracking all payment attempts and completions.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_proof', 'Awaiting Proof'),
        ('proof_submitted', 'Proof Submitted'),
        ('processing', 'Processing'),
        ('verifying', 'Verifying'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('expired', 'Expired'),
    ]
    
    PAYMENT_PURPOSE = [
        ('policy_premium', 'Policy Premium'),
        ('claim_topup', 'Claim Top-up'),
        ('wallet_deposit', 'Wallet Deposit'),
        ('subscription', 'Subscription'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    
    # Who is paying
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    payment_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Account used for P2P payments"
    )
    
    # Amount
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='KES')
    
    # Purpose and linking
    purpose = models.CharField(max_length=30, choices=PAYMENT_PURPOSE)
    purpose_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference to the item being paid for (policy ID, etc.)"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Provider response data
    provider_reference = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # User-provided payment details
    payment_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Details provided by user (phone number, etc.)"
    )
    
    # Timestamps
    # created_at, updated_at provided by BaseModel
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['reference']),
            models.Index(fields=['purpose', 'purpose_reference']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.currency} {self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_reference():
        """Generate unique payment reference."""
        import random
        import string
        from django.utils import timezone
        
        prefix = timezone.now().strftime('%Y%m%d')
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"PAY-{prefix}-{suffix}"
    
    @property
    def is_pending(self):
        return self.status in ['pending', 'awaiting_proof', 'proof_submitted', 'processing', 'verifying']
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def requires_proof(self):
        return self.payment_method.requires_proof


class PaymentProof(BaseModel):
    """
    Proof of payment for P2P transactions.
    Inspired by Binance P2P verification flow.
    """
    PROOF_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('requires_more', 'Requires More Info'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='proofs'
    )
    
    # Proof details
    proof_image = models.ImageField(
        upload_to='payment_proofs/%Y/%m/',
        help_text="Screenshot or photo of payment confirmation"
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Transaction ID from payment provider (M-Pesa code, etc.)"
    )
    sender_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name on the sending account"
    )
    sender_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Phone/Account number used for payment"
    )
    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount shown in proof"
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/time of payment as shown in proof"
    )
    
    # Additional proof data
    additional_notes = models.TextField(blank=True)
    
    # Verification
    status = models.CharField(max_length=20, choices=PROOF_STATUS, default='pending')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_proofs'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Payment Proof'
        verbose_name_plural = 'Payment Proofs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Proof for {self.payment.reference} ({self.status})"
    
    def approve(self, verified_by):
        """Approve this proof and complete the payment."""
        from django.utils import timezone
        
        self.status = 'approved'
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.save()
        
        # Update payment status
        self.payment.status = 'completed'
        self.payment.completed_at = timezone.now()
        self.payment.save()
        
        # Trigger payment completion signal
        from apps.payments.signals import payment_completed
        payment_completed.send(sender=self.__class__, payment=self.payment)
    
    def reject(self, verified_by, reason):
        """Reject this proof."""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.rejection_reason = reason
        self.save()
        
        # Update payment to allow retry
        self.payment.status = 'awaiting_proof'
        self.payment.save()


class PaymentNotification(SimpleBaseModel):
    """
    Track payment notifications (webhooks, callbacks, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(max_length=50)
    raw_data = models.JSONField()
    processed = models.BooleanField(default=False)
    processing_result = models.JSONField(default=dict, blank=True)
    
    # created_at provided by BaseModel
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Payment Notification'
        verbose_name_plural = 'Payment Notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.created_at}"
