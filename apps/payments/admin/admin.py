"""
Admin configuration for Payments app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from apps.payments.models import (
    PaymentMethod, PaymentAccount, Payment, PaymentProof, PaymentNotification
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'method_type', 'requires_proof', 'is_active', 'display_order']
    list_filter = ['method_type', 'is_active', 'requires_proof']
    search_fields = ['name', 'code']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'method_type', 'description')
        }),
        ('Display', {
            'fields': ('icon', 'display_order', 'instructions')
        }),
        ('Configuration', {
            'fields': ('is_active', 'requires_proof', 'min_amount', 'max_amount')
        }),
        ('Advanced', {
            'fields': ('payment_details_schema', 'provider_config'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentAccount)
class PaymentAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'payment_method', 'is_active', 'display_order']
    list_filter = ['payment_method', 'is_active']
    search_fields = ['name']
    ordering = ['display_order']


class PaymentProofInline(admin.TabularInline):
    model = PaymentProof
    extra = 0
    readonly_fields = ['id', 'proof_image', 'transaction_reference', 'status', 'created_at']
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'user_email', 'payment_method', 'amount_display', 
        'purpose', 'status_badge', 'created_at'
    ]
    list_filter = ['status', 'purpose', 'payment_method', 'created_at']
    search_fields = ['reference', 'user__email', 'purpose_reference']
    readonly_fields = [
        'id', 'reference', 'created_at', 'updated_at', 'completed_at'
    ]
    date_hierarchy = 'created_at'
    inlines = [PaymentProofInline]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'reference', 'user')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_account', 'amount', 'currency')
        }),
        ('Purpose', {
            'fields': ('purpose', 'purpose_reference')
        }),
        ('Status', {
            'fields': ('status', 'provider_reference', 'provider_response')
        }),
        ('Notes', {
            'fields': ('notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def amount_display(self, obj):
        return f"{obj.currency} {obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'awaiting_proof': '#8b5cf6',
            'proof_submitted': '#3b82f6',
            'processing': '#6366f1',
            'verifying': '#06b6d4',
            'completed': '#10b981',
            'failed': '#ef4444',
            'cancelled': '#6b7280',
            'refunded': '#f97316',
            'expired': '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    @admin.action(description='Mark selected as completed')
    def mark_as_completed(self, request, queryset):
        from apps.payments.services import PaymentService
        count = 0
        for payment in queryset.filter(status__in=['pending', 'processing', 'verifying']):
            PaymentService.complete_payment(payment)
            count += 1
        self.message_user(request, f'{count} payment(s) marked as completed.')
    
    @admin.action(description='Mark selected as failed')
    def mark_as_failed(self, request, queryset):
        count = queryset.filter(status='pending').update(status='failed')
        self.message_user(request, f'{count} payment(s) marked as failed.')


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'payment_ref', 'transaction_reference', 
        'status_badge', 'verified_by', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['payment__reference', 'transaction_reference', 'sender_name']
    readonly_fields = ['id', 'payment', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'payment', 'proof_image')
        }),
        ('Payment Details', {
            'fields': ('transaction_reference', 'sender_name', 'sender_number', 'amount_paid', 'payment_date')
        }),
        ('Verification', {
            'fields': ('status', 'verified_by', 'verified_at', 'rejection_reason')
        }),
        ('Notes', {
            'fields': ('additional_notes',)
        }),
    )
    
    actions = ['approve_proofs', 'reject_proofs']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def payment_ref(self, obj):
        return obj.payment.reference
    payment_ref.short_description = 'Payment'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444',
            'requires_more': '#8b5cf6',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    @admin.action(description='Approve selected proofs')
    def approve_proofs(self, request, queryset):
        """Approve proofs using PaymentService."""
        from apps.payments.services import PaymentService
        
        count = 0
        for proof in queryset.filter(status='pending'):
            try:
                PaymentService.verify_proof(proof, request.user, approved=True)
                count += 1
            except Exception as e:
                self.message_user(request, f'Error approving proof: {e}', level='error')
        self.message_user(request, f'{count} proof(s) approved.')
    
    @admin.action(description='Reject selected proofs')
    def reject_proofs(self, request, queryset):
        """Reject proofs using PaymentService."""
        from apps.payments.services import PaymentService
        
        count = 0
        for proof in queryset.filter(status='pending'):
            try:
                PaymentService.verify_proof(
                    proof, 
                    request.user, 
                    approved=False,
                    rejection_reason='Rejected via admin action'
                )
                count += 1
            except Exception as e:
                self.message_user(request, f'Error rejecting proof: {e}', level='error')
        self.message_user(request, f'{count} proof(s) rejected.')


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'payment_method', 'notification_type', 'processed', 'created_at']
    list_filter = ['payment_method', 'notification_type', 'processed', 'created_at']
    readonly_fields = ['id', 'payment', 'payment_method', 'notification_type', 'raw_data', 'created_at']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
