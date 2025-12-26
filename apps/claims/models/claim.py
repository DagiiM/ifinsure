"""
Claims models - Claims processing and management.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel, SimpleBaseModel


class Claim(BaseModel):
    """
    Insurance claims.
    Tracks claims from submission through settlement.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('investigating', 'Investigating'),
        ('approved', 'Approved'),
        ('partially_approved', 'Partially Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    claim_number = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    
    # Relationships
    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.PROTECT,
        related_name='claims'
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='claims'
    )
    assigned_adjuster = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims',
        limit_choices_to={'user_type__in': ['staff', 'agent']}
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        db_index=True
    )
    
    # Incident details
    incident_date = models.DateField()
    incident_time = models.TimeField(null=True, blank=True)
    incident_description = models.TextField()
    incident_location = models.CharField(max_length=500, blank=True)
    
    # Financial
    claimed_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    approved_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Processing
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims'
    )
    rejection_reason = models.TextField(blank=True)
    adjuster_notes = models.TextField(blank=True, help_text='Internal notes for adjusters')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Claim'
        verbose_name_plural = 'Claims'
        indexes = [
            models.Index(fields=['policy', 'status']),
            models.Index(fields=['claim_number']),
            models.Index(fields=['claimant', 'status']),
            models.Index(fields=['assigned_adjuster', 'status']),
        ]
    
    def __str__(self):
        return f"{self.claim_number} - {self.policy.policy_number}"
    
    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = self._generate_claim_number()
        super().save(*args, **kwargs)
    
    def _generate_claim_number(self):
        """Generate unique claim number."""
        prefix = f"CLM-{timezone.now().strftime('%Y%m')}"
        last = Claim.objects.filter(
            claim_number__startswith=prefix
        ).order_by('-claim_number').first()
        if last:
            seq = int(last.claim_number.split('-')[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"
    
    @property
    def days_since_submission(self):
        """Days since claim was submitted."""
        if not self.submitted_at:
            return None
        delta = timezone.now() - self.submitted_at
        return delta.days
    
    @property
    def is_overdue(self):
        """Check if claim processing is overdue (>30 days for standard)."""
        if self.status in ['paid', 'closed', 'rejected']:
            return False
        days = self.days_since_submission
        return days and days > 30


class ClaimDocument(BaseModel):
    """Documents supporting claims."""
    DOCUMENT_TYPE_CHOICES = [
        ('photo', 'Photograph'),
        ('report', 'Incident Report'),
        ('receipt', 'Receipt/Invoice'),
        ('estimate', 'Repair Estimate'),
        ('id', 'Identification'),
        ('medical', 'Medical Record'),
        ('police', 'Police Report'),
        ('witness', 'Witness Statement'),
        ('other', 'Other'),
    ]
    
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='claims/documents/%Y/%m/')
    description = models.TextField(blank=True)
    
    # uploaded_by replaced by created_by from BaseModel
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Claim Document'
        verbose_name_plural = 'Claim Documents'
    
    def __str__(self):
        return f"{self.title} - {self.claim.claim_number}"


class ClaimNote(BaseModel):
    """Internal notes on claims."""
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    
    # author replaced by created_by from BaseModel
    
    content = models.TextField()
    is_internal = models.BooleanField(
        default=True,
        help_text='Internal notes are not visible to customers'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Claim Note'
        verbose_name_plural = 'Claim Notes'
    
    def __str__(self):
        return f"Note on {self.claim.claim_number} by {self.created_by}"


class ClaimStatusHistory(BaseModel):
    """Track claim status changes for audit."""
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    
    # changed_by replaced by created_by from BaseModel
    # changed_at replaced by created_at from BaseModel
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Status History'
        verbose_name_plural = 'Status Histories'
    
    def __str__(self):
        return f"{self.claim.claim_number}: {self.old_status} → {self.new_status}"
