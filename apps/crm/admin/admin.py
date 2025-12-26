"""
Admin configuration for CRM models.
"""
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from apps.crm.models import (
    InsuranceProvider, ProviderContact, ProductCategory, 
    InsuranceProduct, ProductBenefit, CustomerTag, Customer,
    CustomerDocument, Lead, Communication
)


class ProviderContactInline(admin.TabularInline):
    model = ProviderContact
    extra = 1


@admin.register(InsuranceProvider)
class InsuranceProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'provider_type', 'phone', 'email', 'default_commission_rate', 'api_status', 'is_active']
    list_filter = ['provider_type', 'is_active', 'api_enabled']
    search_fields = ['name', 'code', 'email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProviderContactInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'provider_type', 'logo', 'primary_color')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'alt_phone', 'website', 'address', 'city', 'country')
        }),
        ('Business Details', {
            'fields': ('registration_number', 'ira_license', 'kra_pin', 'default_commission_rate')
        }),
        ('API Integration', {
            'fields': ('api_enabled', 'api_base_url', 'api_credentials'),
            'classes': ('collapse',)
        }),
        ('Contract', {
            'fields': ('contract_start', 'contract_end', 'contract_document'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def api_status(self, obj):
        if obj.api_enabled:
            return format_html('<span style="color: #22c55e;">●</span> Enabled')
        return format_html('<span style="color: #9ca3af;">○</span> Disabled')
    api_status.short_description = 'API'


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'display_order', 'product_count', 'is_active']
    list_editable = ['display_order', 'is_active']
    search_fields = ['name', 'code']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class ProductBenefitInline(admin.TabularInline):
    model = ProductBenefit
    extra = 1


@admin.register(InsuranceProduct)
class InsuranceProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'category', 'premium_display', 'commission_display', 'payment_mode_display', 'featured', 'is_active']
    list_filter = ['provider', 'category', 'is_active', 'featured', 'premium_type', 'application_payment_mode']
    search_fields = ['name', 'code', 'provider__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProductBenefitInline]
    
    fieldsets = (
        (None, {
            'fields': ('provider', 'category', 'name', 'code', 'short_description', 'description')
        }),
        ('Pricing', {
            'fields': ('premium_type', 'base_premium', 'min_premium', 'max_premium', 'pricing_rules')
        }),
        ('Coverage', {
            'fields': ('min_sum_insured', 'max_sum_insured', 'coverage_details', 'exclusions', 'terms_conditions')
        }),
        ('Commission', {
            'fields': ('commission_type', 'commission_rate')
        }),
        ('Application Payment', {
            'fields': ('application_payment_mode', 'convenience_fee', 'convenience_fee_type', 'allow_partial_payment'),
            'description': 'Configure what payment is required when an application is submitted.'
        }),
        ('Documents', {
            'fields': ('brochure', 'policy_wording'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('default_duration_months', 'requires_underwriting', 'auto_renew_enabled', 'featured', 'display_order', 'is_active')
        }),
    )
    
    def premium_display(self, obj):
        if obj.premium_type == 'percentage':
            return f"{obj.base_premium}%"
        elif obj.premium_type == 'fixed':
            return f"KES {obj.base_premium:,.0f}"
        return "Calculated"
    premium_display.short_description = 'Premium'
    
    def commission_display(self, obj):
        rate = obj.effective_commission_rate
        return f"{rate}%"
    commission_display.short_description = 'Commission'
    
    def payment_mode_display(self, obj):
        mode_icons = {
            'none': format_html('<span style="color: #9ca3af;">○</span> None'),
            'convenience_only': format_html('<span style="color: #f59e0b;">◐</span> Fee Only'),
            'full': format_html('<span style="color: #22c55e;">●</span> Full'),
        }
        return mode_icons.get(obj.application_payment_mode, obj.application_payment_mode)
    payment_mode_display.short_description = 'App Payment'


@admin.register(CustomerTag)
class CustomerTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'customer_count']
    
    def customer_count(self, obj):
        return obj.customers.count()
    customer_count.short_description = 'Customers'


class CustomerDocumentInline(admin.TabularInline):
    model = CustomerDocument
    extra = 0
    readonly_fields = ['created_at', 'verified_by', 'verified_at']


class CommunicationInline(admin.TabularInline):
    model = Communication
    extra = 0
    readonly_fields = ['channel', 'direction', 'content', 'performed_by', 'created_at']
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_number', 'display_name', 'customer_type', 'phone', 'email', 'lifecycle_stage', 'assigned_agent', 'created_at']
    list_filter = ['customer_type', 'lifecycle_stage', 'source', 'created_at']
    search_fields = ['customer_number', 'first_name', 'last_name', 'company_name', 'email', 'phone', 'id_number']
    readonly_fields = ['customer_number', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'assigned_agent', 'created_by']
    filter_horizontal = ['tags']
    inlines = [CustomerDocumentInline, CommunicationInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('customer_type', 'customer_number', 'user')
        }),
        ('Individual Details', {
            'fields': ('first_name', 'middle_name', 'last_name', 'id_type', 'id_number', 'date_of_birth', 'gender', 'occupation', 'employer'),
            'classes': ('collapse',)
        }),
        ('Corporate Details', {
            'fields': ('company_name', 'company_registration', 'kra_pin', 'industry', 'number_of_employees'),
            'classes': ('collapse',)
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'alt_phone', 'whatsapp', 'address', 'city', 'county', 'postal_code', 'country')
        }),
        ('CRM', {
            'fields': ('source', 'referral_source', 'assigned_agent', 'lifecycle_stage', 'lead_score', 'tags')
        }),
        ('Preferences', {
            'fields': ('preferred_contact_method', 'preferred_language', 'marketing_consent', 'sms_consent', 'email_consent'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_name(self, obj):
        return str(obj)
    display_name.short_description = 'Name'


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['lead_number', 'name', 'phone', 'status_display', 'priority_display', 'interest_category', 'assigned_to', 'follow_up_date', 'created_at']
    list_filter = ['status', 'priority', 'source', 'interest_category', 'created_at']
    search_fields = ['lead_number', 'name', 'email', 'phone', 'company']
    readonly_fields = ['lead_number', 'converted_at', 'created_at', 'updated_at']
    raw_id_fields = ['customer', 'assigned_to', 'created_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Lead Info', {
            'fields': ('lead_number', 'name', 'email', 'phone', 'company')
        }),
        ('Interest', {
            'fields': ('source', 'interest_category', 'interest_product', 'estimated_value', 'notes')
        }),
        ('Pipeline', {
            'fields': ('status', 'priority', 'assigned_to', 'follow_up_date', 'last_contact_at')
        }),
        ('Conversion', {
            'fields': ('customer', 'converted_at', 'lost_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_contacted', 'mark_qualified', 'convert_to_customer']
    
    def status_display(self, obj):
        colors = {
            'new': '#60a5fa',
            'contacted': '#818cf8',
            'qualified': '#f59e0b',
            'proposal': '#a78bfa',
            'negotiation': '#f97316',
            'won': '#22c55e',
            'lost': '#ef4444',
        }
        return format_html(
            '<span style="padding: 2px 8px; border-radius: 4px; background: {}; color: white; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def priority_display(self, obj):
        icons = ['🔥', '⚡', '●', '○', '·']
        return icons[obj.priority - 1] if obj.priority <= 5 else '·'
    priority_display.short_description = 'P'
    
    @admin.action(description='📞 Mark as Contacted')
    def mark_contacted(self, request, queryset):
        """Update lead status using CRMService."""
        from apps.crm.services import CRMService
        
        count = 0
        for lead in queryset:
            try:
                CRMService.update_lead_status(lead, 'contacted', request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f'Error updating lead {lead.lead_number}: {e}', messages.WARNING)
        self.message_user(request, f'{count} leads marked as contacted.', messages.SUCCESS)
    
    @admin.action(description='✅ Mark as Qualified')
    def mark_qualified(self, request, queryset):
        """Update lead status using CRMService."""
        from apps.crm.services import CRMService
        
        count = 0
        for lead in queryset:
            try:
                CRMService.update_lead_status(lead, 'qualified', request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f'Error updating lead {lead.lead_number}: {e}', messages.WARNING)
        self.message_user(request, f'{count} leads marked as qualified.', messages.SUCCESS)
    
    @admin.action(description='🔄 Convert to Customer')
    def convert_to_customer(self, request, queryset):
        """Convert leads to customers using CRMService."""
        from apps.crm.services import CRMService
        
        count = 0
        for lead in queryset.filter(customer__isnull=True):
            try:
                # First update to 'won' status, then convert
                CRMService.update_lead_status(lead, 'won', request.user, notes='Converted via admin action')
                lead.convert_to_customer(user=request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f'Error converting lead {lead.lead_number}: {e}', messages.WARNING)
        self.message_user(request, f'{count} leads converted to customers.', messages.SUCCESS)


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ['target', 'channel', 'direction', 'subject_short', 'performed_by', 'follow_up_required', 'created_at']
    list_filter = ['channel', 'direction', 'follow_up_required', 'created_at']
    search_fields = ['subject', 'content', 'customer__first_name', 'customer__last_name', 'lead__name']
    readonly_fields = ['created_at']
    raw_id_fields = ['customer', 'lead', 'performed_by']
    date_hierarchy = 'created_at'
    
    def target(self, obj):
        return obj.customer or obj.lead
    target.short_description = 'Customer/Lead'
    
    def subject_short(self, obj):
        return obj.subject[:40] + '...' if len(obj.subject) > 40 else obj.subject
    subject_short.short_description = 'Subject'
