"""
Accountability Mixin - GDPR/Data Protection Compliance at Model Level.

Provides:
- Data access logging
- Consent tracking
- Data retention policies
- Right to be forgotten support
- Data portability helpers
"""
from django.db import models
from django.utils import timezone
from django.conf import settings


class AccountabilityMixin(models.Model):
    """
    Mixin for GDPR/Data Protection compliance at model level.
    
    Features:
    - Tracks who created/modified records
    - Records consent for data processing
    - Supports data retention policies
    - Enables data portability (export)
    - Supports right to be forgotten (anonymization)
    
    Usage:
        class Customer(AccountabilityMixin, BaseModel):
            GDPR_FIELDS = ['email', 'phone', 'address']  # Fields to anonymize
            RETENTION_DAYS = 365 * 7  # 7 years retention
            
            name = models.CharField(max_length=100)
            email = models.EmailField()
    """
    
    # Who created/modified this record
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        help_text='User who created this record'
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified',
        help_text='User who last modified this record'
    )
    
    # Consent tracking
    consent_given = models.BooleanField(
        default=False,
        help_text='Whether user consented to data processing'
    )
    consent_given_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When consent was given'
    )
    consent_ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address when consent was given'
    )
    
    # Data protection
    is_anonymized = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this record has been anonymized (right to be forgotten)'
    )
    anonymized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this record was anonymized'
    )
    
    # Retention
    retain_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Date until which this record must be retained'
    )
    
    class Meta:
        abstract = True
    
    # Override in subclass to specify which fields contain PII
    GDPR_FIELDS = []
    
    # Override in subclass to set retention period (days)
    RETENTION_DAYS = None
    
    def record_consent(self, ip_address=None):
        """Record that consent was given for data processing."""
        self.consent_given = True
        self.consent_given_at = timezone.now()
        self.consent_ip_address = ip_address
        self.save(update_fields=['consent_given', 'consent_given_at', 'consent_ip_address'])
    
    def revoke_consent(self):
        """Revoke consent for data processing."""
        self.consent_given = False
        self.save(update_fields=['consent_given'])
    
    def anonymize(self, user=None):
        """
        Anonymize PII fields (right to be forgotten).
        Override GDPR_FIELDS in subclass to specify which fields to anonymize.
        """
        if self.is_anonymized:
            return
        
        for field_name in self.GDPR_FIELDS:
            field = self._meta.get_field(field_name)
            if isinstance(field, models.EmailField):
                setattr(self, field_name, f'anonymized_{self.pk}@deleted.local')
            elif isinstance(field, models.CharField):
                setattr(self, field_name, '[REDACTED]')
            elif isinstance(field, (models.TextField,)):
                setattr(self, field_name, '[REDACTED]')
            elif isinstance(field, models.GenericIPAddressField):
                setattr(self, field_name, None)
        
        self.is_anonymized = True
        self.anonymized_at = timezone.now()
        self.modified_by = user
        self.save()
    
    def set_retention(self, days=None):
        """Set data retention period."""
        retention_days = days or self.RETENTION_DAYS
        if retention_days:
            from datetime import timedelta
            self.retain_until = timezone.now() + timedelta(days=retention_days)
            self.save(update_fields=['retain_until'])
    
    def export_data(self):
        """
        Export all data for this record (data portability).
        Returns a dictionary of all field values.
        """
        data = {}
        for field in self._meta.fields:
            value = getattr(self, field.name)
            # Handle special types
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            elif hasattr(value, 'pk'):
                value = str(value.pk)
            data[field.name] = value
        return data
    
    def get_accountability_log(self):
        """Get accountability information for this record."""
        return {
            'created_by': str(self.created_by) if self.created_by else None,
            'modified_by': str(self.modified_by) if self.modified_by else None,
            'consent_given': self.consent_given,
            'consent_given_at': self.consent_given_at.isoformat() if self.consent_given_at else None,
            'is_anonymized': self.is_anonymized,
            'retain_until': self.retain_until.isoformat() if self.retain_until else None,
        }
