"""
Policies models - Insurance products, policies, and applications.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel
from apps.crm.models.crm import InsuranceProduct


# InsuranceProduct moved to CRM app to resolve duplication


class Policy(BaseModel):
    """
    Active insurance policies.
    Represents an active contract between customer and insurer.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Activation'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('lapsed', 'Lapsed'),
    ]
    
    PAYMENT_FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ]
    
    policy_number = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    
    # Relationships
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='policies',
        limit_choices_to={'user_type': 'customer'}
    )
    product = models.ForeignKey(
        InsuranceProduct,
        on_delete=models.PROTECT,
        related_name='policies'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_policies',
        limit_choices_to={'user_type': 'agent'}
    )
    
    # Status and dates
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Financial
    premium_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    coverage_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_frequency = models.CharField(
        max_length=20,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default='monthly'
    )
    
    # Additional info
    beneficiary_name = models.CharField(max_length=200, blank=True)
    beneficiary_relationship = models.CharField(max_length=100, blank=True)
    beneficiary_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Policy'
        verbose_name_plural = 'Policies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['policy_number']),
            models.Index(fields=['agent', 'status']),
        ]
    
    def __str__(self):
        return f"{self.policy_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        if not self.policy_number:
            self.policy_number = self._generate_policy_number()
        super().save(*args, **kwargs)
    
    def _generate_policy_number(self):
        """Generate unique policy number."""
        prefix = f"POL-{timezone.now().strftime('%Y%m')}"
        last = Policy.objects.filter(
            policy_number__startswith=prefix
        ).order_by('-policy_number').first()
        if last:
            seq = int(last.policy_number.split('-')[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"
    
    @property
    def is_expired(self):
        """Check if policy is expired."""
        return self.end_date < timezone.now().date()
    
    @property
    def days_until_expiry(self):
        """Days until policy expires."""
        delta = self.end_date - timezone.now().date()
        return delta.days
    
    @property
    def is_expiring_soon(self):
        """Check if policy expires within 30 days."""
        return 0 < self.days_until_expiry <= 30


class PolicyApplication(BaseModel):
    """
    Policy application records.
    Tracks applications from submission to approval/rejection.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    application_number = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    
    # Relationships
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    product = models.ForeignKey(
        InsuranceProduct,
        on_delete=models.PROTECT,
        related_name='applications'
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_applications',
        limit_choices_to={'user_type': 'agent'}
    )
    
    # Application details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    requested_coverage = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    requested_term_months = models.PositiveIntegerField(default=12)
    payment_frequency = models.CharField(
        max_length=20,
        choices=Policy.PAYMENT_FREQUENCY_CHOICES,
        default='monthly'
    )
    calculated_premium = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Beneficiary
    beneficiary_name = models.CharField(max_length=200, blank=True)
    beneficiary_relationship = models.CharField(max_length=100, blank=True)
    beneficiary_phone = models.CharField(max_length=20, blank=True)
    
    # Processing
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Link to created policy
    policy = models.OneToOneField(
        Policy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application'
    )
    
    # Payment Tracking
    PAYMENT_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('refunded', 'Refunded'),
    ]
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    convenience_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Application convenience fee"
    )
    premium_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Premium amount required at application"
    )
    total_payment_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total payment required"
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount already paid"
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference from payment system"
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Policy Application'
        verbose_name_plural = 'Policy Applications'
        indexes = [
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['application_number']),
        ]
    
    def __str__(self):
        return f"{self.application_number} - {self.applicant}"
    
    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self._generate_application_number()
        super().save(*args, **kwargs)
    
    def _generate_application_number(self):
        """Generate unique application number."""
        prefix = f"APP-{timezone.now().strftime('%Y%m')}"
        last = PolicyApplication.objects.filter(
            application_number__startswith=prefix
        ).order_by('-application_number').first()
        if last:
            seq = int(last.application_number.split('-')[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"


class PolicyDocument(BaseModel):
    """Documents associated with policies."""
    DOCUMENT_TYPE_CHOICES = [
        ('certificate', 'Policy Certificate'),
        ('terms', 'Terms & Conditions'),
        ('endorsement', 'Endorsement'),
        ('renewal', 'Renewal Notice'),
        ('other', 'Other'),
    ]
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='policies/documents/%Y/%m/')
    description = models.TextField(blank=True)
    
    # uploaded_by replaced by created_by from BaseModel
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.policy.policy_number}"
