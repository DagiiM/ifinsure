"""
Notification admin configuration.
"""
from django.contrib import admin
from django.utils.html import format_html
from ..models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification model."""
    
    list_display = [
        'title', 'recipient', 'notification_type', 'channel',
        'is_read_display', 'delivery_status', 'created_at'
    ]
    list_filter = [
        'notification_type', 'channel', 'is_read', 
        'is_archived', 'delivery_status', 'created_at'
    ]
    search_fields = ['title', 'message', 'recipient__email', 'recipient__first_name']
    readonly_fields = ['created_at', 'updated_at', 'read_at', 'delivered_at', 'archived_at']
    raw_id_fields = ['recipient', 'sender']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification', {
            'fields': ('recipient', 'sender', 'title', 'message')
        }),
        ('Type & Channel', {
            'fields': ('notification_type', 'channel', 'icon', 'icon_color', 'priority')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id', 'action_url'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_archived', 'archived_at')
        }),
        ('Delivery', {
            'fields': ('delivery_status', 'delivered_at', 'delivery_error'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_read_display(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange;">○ Unread</span>')
    is_read_display.short_description = 'Status'
    
    actions = ['mark_as_read', 'mark_as_unread', 'archive_selected']
    
    @admin.action(description='Mark selected notifications as read')
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{count} notifications marked as read.')
    
    @admin.action(description='Mark selected notifications as unread')
    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{count} notifications marked as unread.')
    
    @admin.action(description='Archive selected notifications')
    def archive_selected(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(is_archived=True, archived_at=timezone.now())
        self.message_user(request, f'{count} notifications archived.')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationPreference model."""
    
    list_display = [
        'user', 'email_enabled', 'sms_enabled', 
        'push_enabled', 'in_app_enabled', 'quiet_hours_enabled'
    ]
    list_filter = [
        'email_enabled', 'sms_enabled', 'push_enabled', 
        'in_app_enabled', 'quiet_hours_enabled'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Channels', {
            'fields': ('email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled')
        }),
        ('Policy Notifications', {
            'fields': ('notify_policy_created', 'notify_policy_updated',
                      'notify_policy_expiring', 'notify_policy_expired'),
            'classes': ('collapse',)
        }),
        ('Claim Notifications', {
            'fields': ('notify_claim_submitted', 'notify_claim_updated',
                      'notify_claim_approved', 'notify_claim_rejected'),
            'classes': ('collapse',)
        }),
        ('Payment Notifications', {
            'fields': ('notify_payment_due', 'notify_payment_received', 'notify_payment_overdue'),
            'classes': ('collapse',)
        }),
        ('System Notifications', {
            'fields': ('notify_system_updates', 'notify_security_alerts', 'notify_promotions'),
            'classes': ('collapse',)
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',)
        }),
        ('Email Digest', {
            'fields': ('email_digest_enabled', 'email_digest_frequency'),
            'classes': ('collapse',)
        }),
    )
