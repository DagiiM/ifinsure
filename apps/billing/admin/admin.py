"""
Billing admin configuration.
"""
from django.contrib import admin
from apps.billing.models import Invoice, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['payment_reference', 'created_at', 'received_by']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer', 'policy', 'status',
        'amount', 'paid_amount', 'due_date', 'issued_date'
    ]
    list_filter = ['status', 'issued_date', 'due_date']
    search_fields = ['invoice_number', 'customer__email', 'customer__first_name']
    raw_id_fields = ['customer', 'policy']
    date_hierarchy = 'issued_date'
    ordering = ['-issued_date']
    inlines = [PaymentInline]
    
    fieldsets = (
        (None, {'fields': ('invoice_number', 'status', 'is_active')}),
        ('Customer', {'fields': ('customer', 'policy')}),
        ('Dates', {'fields': ('due_date',)}),
        ('Financial', {'fields': ('amount', 'paid_amount')}),
        ('Details', {'fields': ('description', 'notes')}),
    )
    
    readonly_fields = ['invoice_number', 'paid_amount']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_reference', 'invoice', 'amount', 'payment_method',
        'status', 'created_at', 'received_by'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['payment_reference', 'invoice__invoice_number', 'transaction_id']
    raw_id_fields = ['invoice', 'received_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = ['payment_reference', 'created_at']
