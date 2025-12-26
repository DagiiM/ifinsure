"""
Policies admin configuration.
"""
from django.contrib import admin
from apps.policies.models import InsuranceProduct, Policy, PolicyApplication, PolicyDocument


class PolicyDocumentInline(admin.TabularInline):
    """Inline for policy documents."""
    model = PolicyDocument
    extra = 0
    readonly_fields = ['created_by', 'created_at']


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    """Admin for policies."""
    list_display = ['policy_number', 'customer', 'product', 'status', 'premium_amount', 'start_date', 'end_date']
    list_filter = ['status', 'product__category', 'payment_frequency', 'created_at']
    search_fields = ['policy_number', 'customer__email', 'customer__first_name', 'customer__last_name']
    raw_id_fields = ['customer', 'agent']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    inlines = [PolicyDocumentInline]
    
    fieldsets = (
        (None, {'fields': ('policy_number', 'status', 'is_active')}),
        ('Parties', {'fields': ('customer', 'product', 'agent')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Financial', {'fields': ('premium_amount', 'coverage_amount', 'payment_frequency')}),
        ('Beneficiary', {'fields': ('beneficiary_name', 'beneficiary_relationship', 'beneficiary_phone')}),
        ('Notes', {'fields': ('notes',)}),
    )
    
    readonly_fields = ['policy_number']


@admin.register(PolicyApplication)
class PolicyApplicationAdmin(admin.ModelAdmin):
    """Admin for policy applications."""
    list_display = ['application_number', 'applicant', 'product', 'status', 'payment_status', 'requested_coverage', 'total_payment_due', 'created_at']
    list_filter = ['status', 'payment_status', 'product__category', 'created_at']
    search_fields = ['application_number', 'applicant__email', 'applicant__first_name']
    raw_id_fields = ['applicant', 'assigned_agent', 'reviewed_by', 'policy']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('application_number', 'status', 'is_active')}),
        ('Applicant', {'fields': ('applicant', 'product')}),
        ('Coverage', {'fields': ('requested_coverage', 'requested_term_months', 'payment_frequency', 'calculated_premium')}),
        ('Payment', {
            'fields': ('payment_status', 'convenience_fee_amount', 'premium_amount', 'total_payment_due', 'amount_paid', 'payment_reference', 'paid_at'),
            'description': 'Payment tracking for this application'
        }),
        ('Beneficiary', {'fields': ('beneficiary_name', 'beneficiary_relationship', 'beneficiary_phone')}),
        ('Processing', {'fields': ('assigned_agent', 'submitted_at', 'reviewed_at', 'reviewed_by', 'rejection_reason')}),
        ('Result', {'fields': ('policy',)}),
        ('Notes', {'fields': ('notes',)}),
    )
    
    readonly_fields = ['application_number', 'calculated_premium', 'submitted_at', 'reviewed_at', 'paid_at']

