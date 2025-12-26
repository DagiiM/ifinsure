import json
from django.db import models
from django.utils.text import slugify
from apps.core.models import BaseModel, SimpleBaseModel


class IntegrationCategory(BaseModel):
    """Categories for organizing integrations"""
    
    class CategoryType(models.TextChoices):
        PAYMENT = 'payment', 'Payment Providers'
        SMS = 'sms', 'SMS Gateways'
        EMAIL = 'email', 'Email Services'
        STORAGE = 'storage', 'File Storage'
        ANALYTICS = 'analytics', 'Analytics'
        CRM = 'crm', 'CRM Systems'
    
    name = models.CharField(max_length=50, choices=CategoryType.choices, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='🔌')
    # is_active provided by BaseModel
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Integration Category'
        verbose_name_plural = 'Integration Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.get_name_display()
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def provider_count(self):
        return self.providers.filter(is_available=True).count()
    
    @property
    def active_count(self):
        return IntegrationConfig.objects.filter(
            provider__category=self,
            is_enabled=True
        ).count()


class IntegrationProvider(BaseModel):
    """Available integration providers"""
    
    category = models.ForeignKey(
        IntegrationCategory, 
        on_delete=models.CASCADE,
        related_name='providers'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    logo = models.ImageField(upload_to='integrations/logos/', blank=True, null=True)
    website_url = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    
    # Python class path for the provider implementation
    provider_class = models.CharField(
        max_length=255,
        help_text='Python path to provider class, e.g., apps.integrations.providers.payments.mpesa.MPesaProvider'
    )
    
    # Configuration schema (JSON) - defines what credentials/settings are needed
    config_schema = models.JSONField(
        default=dict,
        help_text='JSON schema defining required configuration fields'
    )
    
    # Feature flags
    supports_webhooks = models.BooleanField(default=False)
    supports_sandbox = models.BooleanField(default=True)
    supports_refunds = models.BooleanField(default=False)
    
    # Availability
    is_available = models.BooleanField(default=True)
    countries = models.JSONField(
        default=list,
        help_text='List of ISO country codes where this provider is available'
    )
    
    class Meta:
        verbose_name = 'Integration Provider'
        verbose_name_plural = 'Integration Providers'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_provider_instance(self, config):
        """Dynamically load and instantiate the provider class"""
        from django.utils.module_loading import import_string
        provider_class = import_string(self.provider_class)
        return provider_class(config)


class IntegrationConfig(BaseModel):
    """Active integration configurations"""
    
    class Environment(models.TextChoices):
        SANDBOX = 'sandbox', 'Sandbox/Test'
        PRODUCTION = 'production', 'Production'
    
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name='configs'
    )
    name = models.CharField(
        max_length=100,
        help_text='A friendly name for this configuration'
    )
    
    # Status
    is_enabled = models.BooleanField(default=False)
    is_primary = models.BooleanField(
        default=False,
        help_text='Primary provider for this category'
    )
    environment = models.CharField(
        max_length=20,
        choices=Environment.choices,
        default=Environment.SANDBOX
    )
    
    # Encrypted credentials (in production, use django-encrypted-model-fields)
    credentials = models.JSONField(
        default=dict,
        help_text='API credentials and configuration'
    )
    
    # Webhook configuration
    webhook_url = models.URLField(blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    
    # Testing
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(max_length=20, blank=True)
    last_test_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Integration Configuration'
        verbose_name_plural = 'Integration Configurations'
        unique_together = ['provider', 'environment']
    
    def __str__(self):
        return f"{self.name} ({self.get_environment_display()})"
    
    def save(self, *args, **kwargs):
        # If this is set as primary, unset other primaries for this category
        if self.is_primary:
            IntegrationConfig.objects.filter(
                provider__category=self.provider.category,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
    
    def get_provider_instance(self):
        """Get an instance of the provider class"""
        return self.provider.get_provider_instance(self)
    
    def test_connection(self):
        """Test the provider connection"""
        from django.utils import timezone
        try:
            provider = self.get_provider_instance()
            success = provider.test_connection()
            self.last_tested_at = timezone.now()
            self.last_test_status = 'success' if success else 'failed'
            self.last_test_message = 'Connection successful' if success else 'Connection failed'
            self.save(update_fields=['last_tested_at', 'last_test_status', 'last_test_message'])
            return success
        except Exception as e:
            self.last_tested_at = timezone.now()
            self.last_test_status = 'error'
            self.last_test_message = str(e)
            self.save(update_fields=['last_tested_at', 'last_test_status', 'last_test_message'])
            return False
    
    def get_credential(self, key, default=None):
        """Safely get a credential value"""
        return self.credentials.get(key, default)


class IntegrationLog(SimpleBaseModel):
    """Log all integration API activities"""
    
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        PENDING = 'pending', 'Pending'
    
    config = models.ForeignKey(
        IntegrationConfig,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Action details
    action = models.CharField(max_length=100)
    request_data = models.JSONField(default=dict)
    response_data = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices)
    error_message = models.TextField(blank=True)
    
    # Performance metrics
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Reference to related object
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    
    # IP and user info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # created_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Integration Log'
        verbose_name_plural = 'Integration Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['config', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.config.provider.name} - {self.action} ({self.status})"
    
    @classmethod
    def log_request(cls, config, action, request_data=None, response_data=None,
                    status='pending', error_message='', response_time_ms=None,
                    reference_type='', reference_id='', ip_address=None):
        """Create a log entry for an API request"""
        return cls.objects.create(
            config=config,
            action=action,
            request_data=request_data or {},
            response_data=response_data or {},
            status=status,
            error_message=error_message,
            response_time_ms=response_time_ms,
            reference_type=reference_type,
            reference_id=reference_id,
            ip_address=ip_address
        )


class WebhookEvent(SimpleBaseModel):
    """Store incoming webhook events for processing"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        PROCESSED = 'processed', 'Processed'
        FAILED = 'failed', 'Failed'
    
    config = models.ForeignKey(
        IntegrationConfig,
        on_delete=models.CASCADE,
        related_name='webhook_events'
    )
    
    # Event data
    event_type = models.CharField(max_length=100, blank=True)
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    # created_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Webhook Event'
        verbose_name_plural = 'Webhook Events'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.config.provider.name} - {self.event_type} ({self.status})"
    
    def mark_processed(self):
        from django.utils import timezone
        self.status = self.Status.PROCESSED
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])
    
    def mark_failed(self, error_message):
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count'])
