"""
CRM models for insurance brokerage operations.
Manages providers, products, customers, leads, and communications.
"""
import uuid
from apps.core.models import BaseModel
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class InsuranceProvider(BaseModel):
    """
    Insurance underwriters/companies whose products we sell.
    E.g., Britam, Jubilee, UAP, APA, CIC, etc.
    """
    PROVIDER_TYPES = [
        ('underwriter', 'Underwriter'),
        ('reinsurer', 'Reinsurer'),
        ('broker', 'Broker'),
        ('agent', 'Agent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES, default='underwriter')
    
    # Branding
    logo = models.ImageField(upload_to='providers/logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    
    # Contact Information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Kenya')
    
    # Business Details
    registration_number = models.CharField(max_length=50, blank=True)
    ira_license = models.CharField(max_length=50, blank=True, help_text="Insurance Regulatory Authority license")
    kra_pin = models.CharField(max_length=20, blank=True)
    
    # Commission
    default_commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('10.00'),
        help_text="Default commission percentage"
    )
    
    # API Integration
    api_enabled = models.BooleanField(default=False)
    api_base_url = models.URLField(blank=True)
    api_credentials = models.JSONField(default=dict, blank=True, help_text="Encrypted API credentials")
    
    # Contract
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    contract_document = models.FileField(upload_to='providers/contracts/', blank=True, null=True)
    
    # Settings
    # is_active, created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Insurance Provider'
        verbose_name_plural = 'Insurance Providers'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def is_contract_active(self):
        if not self.contract_end:
            return True
        return self.contract_end >= timezone.now().date()


class ProviderContact(BaseModel):
    """Contact persons at insurance providers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(InsuranceProvider, on_delete=models.CASCADE, related_name='contacts')
    
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-is_primary', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"


class ProductCategory(BaseModel):
    """Insurance product categories - Motor, Health, Life, etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name or class")
    display_order = models.PositiveIntegerField(default=0)
    # is_active provided by BaseModel
    
    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class InsuranceProduct(BaseModel):
    """
    Insurance products offered by providers.
    E.g., "Britam Motor Comprehensive", "Jubilee Health Cover"
    """
    PREMIUM_TYPES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Sum Insured'),
        ('calculated', 'Calculated by Rules'),
    ]
    
    COMMISSION_TYPES = [
        ('percentage', 'Percentage of Premium'),
        ('fixed', 'Fixed Amount'),
    ]
    
    CATEGORY_CHOICES = [
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('auto', 'Auto Insurance'),
        ('home', 'Home Insurance'),
        ('business', 'Business Insurance'),
        ('travel', 'Travel Insurance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        InsuranceProvider, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='products'
    )
    
    # Basic Info
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, unique=True, db_index=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    
    # Pricing
    base_premium = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    premium_type = models.CharField(max_length=20, choices=PREMIUM_TYPES, default='percentage')
    min_premium = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    max_premium = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Pricing Rules (for calculated premiums)
    pricing_rules = models.JSONField(
        default=dict, 
        blank=True,
        help_text="JSON rules for premium calculation"
    )
    
    # Coverage
    min_sum_insured = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    max_sum_insured = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    coverage_details = models.JSONField(default=dict, blank=True)
    exclusions = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    # Documents
    brochure = models.FileField(upload_to='products/brochures/', blank=True, null=True)
    policy_wording = models.FileField(upload_to='products/wordings/', blank=True, null=True)
    
    # Commission
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Override provider's default rate"
    )
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES, default='percentage')
    
    # Duration
    default_duration_months = models.PositiveIntegerField(default=12)
    min_term_months = models.PositiveIntegerField(default=12)
    max_term_months = models.PositiveIntegerField(default=120)
    
    # Features
    features = models.JSONField(
        default=list,
        blank=True,
        help_text='List of product features'
    )
    
    # Settings
    # is_active provided by BaseModel
    requires_underwriting = models.BooleanField(default=False)
    auto_renew_enabled = models.BooleanField(default=True)
    
    # Application Payment Configuration
    APPLICATION_PAYMENT_MODES = [
        ('none', 'No Payment Required'),
        ('convenience_only', 'Convenience Fee Only'),
        ('full', 'Full Payment (Fee + Premium)'),
    ]
    
    FEE_TYPES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Premium'),
    ]
    
    application_payment_mode = models.CharField(
        max_length=20,
        choices=APPLICATION_PAYMENT_MODES,
        default='convenience_only',
        help_text="Payment required when submitting application"
    )
    convenience_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('500.00'),
        help_text="Application/Processing fee"
    )
    convenience_fee_type = models.CharField(
        max_length=20,
        choices=FEE_TYPES,
        default='fixed',
        help_text="How convenience fee is calculated"
    )
    allow_partial_payment = models.BooleanField(
        default=False,
        help_text="Allow customers to pay in installments after approval"
    )
    
    # Display
    featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    
    # created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Insurance Product'
        verbose_name_plural = 'Insurance Products'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.provider.code})"
    
    @property
    def effective_commission_rate(self):
        """Get commission rate, falling back to provider default."""
        if self.commission_rate is not None:
            return self.commission_rate
        return self.provider.default_commission_rate
    
    @property
    def min_coverage(self):
        return self.min_sum_insured
        
    @property
    def max_coverage(self):
        return self.max_sum_insured
    
    def get_convenience_fee(self, premium_amount=None):
        """Calculate convenience fee based on configuration."""
        if self.convenience_fee_type == 'percentage' and premium_amount:
            return (self.convenience_fee / Decimal('100')) * premium_amount
        return self.convenience_fee

    def calculate_premium(self, coverage_amount: Decimal) -> Decimal:
        """Calculate premium based on coverage amount."""
        # Simple fallback logic similar to Policies version
        if self.min_sum_insured and self.min_sum_insured > 0:
            rate = self.base_premium / self.min_sum_insured
            return coverage_amount * rate
        # If min_sum_insured is 0 or not set, return base_premium directly
        # or apply it based on premium_type.
        # The original snippet had a typo `return self.base_premium* premium_amount`
        # and an unreachable `return self.convenience_fee`.
        # Assuming if min_sum_insured is not applicable, base_premium is the fixed premium.
        return self.base_premium
    
    def get_application_payment_amount(self, premium_amount=None):
        """
        Calculate total payment required at application based on payment mode.
        Returns tuple of (total_amount, breakdown_dict)
        """
        if self.application_payment_mode == 'none':
            return Decimal('0.00'), {'convenience_fee': Decimal('0.00'), 'premium': Decimal('0.00')}
        
        fee = self.get_convenience_fee(premium_amount)
        
        if self.application_payment_mode == 'convenience_only':
            return fee, {'convenience_fee': fee, 'premium': Decimal('0.00')}
        
        # Full payment mode
        premium = premium_amount or Decimal('0.00')
        total = fee + premium
        return total, {'convenience_fee': fee, 'premium': premium}
    
    @property
    def requires_upfront_payment(self):
        """Check if this product requires payment at application."""
        return self.application_payment_mode != 'none'


class ProductBenefit(BaseModel):
    """Benefits/coverages included in a product."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(InsuranceProduct, on_delete=models.CASCADE, related_name='benefits')
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    coverage_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    coverage_description = models.CharField(max_length=100, blank=True)  # e.g., "Up to KES 1M"
    
    is_included = models.BooleanField(default=True)
    is_optional = models.BooleanField(default=False)
    additional_premium = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"


class CustomerTag(BaseModel):
    """Tags for categorizing customers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6366f1')
    
    def __str__(self):
        return self.name


class Customer(BaseModel):
    """
    Customer/Client records - both individuals and corporates.
    """
    CUSTOMER_TYPES = [
        ('individual', 'Individual'),
        ('corporate', 'Corporate'),
    ]
    
    ID_TYPES = [
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('alien_id', 'Alien ID'),
        ('military_id', 'Military ID'),
        ('birth_certificate', 'Birth Certificate'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    SOURCES = [
        ('walk_in', 'Walk In'),
        ('referral', 'Referral'),
        ('website', 'Website'),
        ('social_media', 'Social Media'),
        ('agent', 'Agent'),
        ('corporate', 'Corporate Partnership'),
        ('renewal', 'Renewal'),
        ('other', 'Other'),
    ]
    
    LIFECYCLE_STAGES = [
        ('lead', 'Lead'),
        ('prospect', 'Prospect'),
        ('customer', 'Customer'),
        ('repeat', 'Repeat Customer'),
        ('vip', 'VIP'),
        ('churned', 'Churned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='individual')
    customer_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # User Link
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='customer_profile'
    )
    
    # Individual Fields
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    id_type = models.CharField(max_length=20, choices=ID_TYPES, blank=True)
    id_number = models.CharField(max_length=50, blank=True, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    
    # Corporate Fields
    company_name = models.CharField(max_length=255, blank=True)
    company_registration = models.CharField(max_length=50, blank=True)
    kra_pin = models.CharField(max_length=20, blank=True, db_index=True)
    industry = models.CharField(max_length=100, blank=True)
    number_of_employees = models.PositiveIntegerField(null=True, blank=True)
    
    # Contact
    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Kenya')
    
    # CRM Fields
    source = models.CharField(max_length=20, choices=SOURCES, blank=True)
    referral_source = models.CharField(max_length=200, blank=True)
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_customers'
    )
    lead_score = models.PositiveIntegerField(default=0)
    lifecycle_stage = models.CharField(max_length=20, choices=LIFECYCLE_STAGES, default='customer')
    tags = models.ManyToManyField(CustomerTag, blank=True, related_name='customers')
    
    # Preferences
    preferred_contact_method = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=20, default='en')
    marketing_consent = models.BooleanField(default=False)
    sms_consent = models.BooleanField(default=True)
    email_consent = models.BooleanField(default=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    # created_by, created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer_number']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['id_number']),
        ]
    
    def __str__(self):
        if self.customer_type == 'corporate':
            return self.company_name or self.customer_number
        return self.full_name or self.customer_number
    
    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)
    
    def save(self, *args, **kwargs):
        if not self.customer_number:
            self.customer_number = self.generate_customer_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_customer_number():
        import random
        import string
        prefix = timezone.now().strftime('%y%m')
        suffix = ''.join(random.choices(string.digits, k=5))
        return f"C{prefix}{suffix}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('crm:customer_detail', kwargs={'pk': self.pk})


class CustomerDocument(BaseModel):
    """Documents uploaded for customers."""
    DOCUMENT_TYPES = [
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('kra_pin', 'KRA PIN Certificate'),
        ('driving_license', 'Driving License'),
        ('photo', 'Passport Photo'),
        ('company_reg', 'Company Registration'),
        ('company_pin', 'Company KRA PIN'),
        ('logbook', 'Vehicle Logbook'),
        ('valuation', 'Valuation Report'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='customers/documents/')
    description = models.CharField(max_length=255, blank=True)
    
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # uploaded_at replaced by created_at
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer} - {self.get_document_type_display()}"


class Lead(BaseModel):
    """
    Sales leads/prospects before they become customers.
    """
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won - Converted'),
        ('lost', 'Lost'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Converts to Customer
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='leads'
    )
    
    # Contact Info
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=255, blank=True)
    
    # Lead Details
    source = models.CharField(max_length=20, choices=Customer.SOURCES, default='website')
    interest_category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    interest_product = models.ForeignKey(
        InsuranceProduct, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Pipeline
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads'
    )
    
    # Tracking
    priority = models.PositiveIntegerField(default=3, help_text="1=Highest, 5=Lowest")
    follow_up_date = models.DateField(null=True, blank=True)
    last_contact_at = models.DateTimeField(null=True, blank=True)
    
    # Conversion
    converted_at = models.DateTimeField(null=True, blank=True)
    lost_reason = models.TextField(blank=True)
    
    # created_by, created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.lead_number} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.lead_number:
            self.lead_number = self.generate_lead_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_lead_number():
        import random
        import string
        prefix = timezone.now().strftime('%y%m')
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"L{prefix}{suffix}"
    
    def convert_to_customer(self, user=None):
        """Convert lead to customer."""
        if self.customer:
            return self.customer
        
        customer = Customer.objects.create(
            customer_type='individual',
            first_name=self.name.split()[0] if self.name else '',
            last_name=' '.join(self.name.split()[1:]) if self.name and ' ' in self.name else '',
            email=self.email,
            phone=self.phone,
            company_name=self.company,
            source=self.source,
            lifecycle_stage='customer',
            created_by=user
        )
        
        self.customer = customer
        self.status = 'won'
        self.converted_at = timezone.now()
        self.save()
        
        return customer


class Communication(BaseModel):
    """
    Communication/interaction history with customers and leads.
    """
    CHANNELS = [
        ('call', 'Phone Call'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('meeting', 'Meeting'),
        ('note', 'Internal Note'),
    ]
    
    DIRECTIONS = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to Customer or Lead
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='communications'
    )
    lead = models.ForeignKey(
        Lead, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='communications'
    )
    
    # Communication Details
    channel = models.CharField(max_length=20, choices=CHANNELS)
    direction = models.CharField(max_length=10, choices=DIRECTIONS, default='outbound')
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    
    # Tracking
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='communications'
    )
    outcome = models.CharField(max_length=255, blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # For calls
    call_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Duration in seconds")
    
    # Attachments
    attachment = models.FileField(upload_to='communications/', blank=True, null=True)
    
    # created_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Communication'
        verbose_name_plural = 'Communications'
        ordering = ['-created_at']
    
    def __str__(self):
        target = self.customer or self.lead
        return f"{self.get_channel_display()} with {target}"
