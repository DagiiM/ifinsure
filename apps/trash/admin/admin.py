"""
Trash admin configuration.
"""
from django.contrib import admin
from django.utils.html import format_html
from ..models import TrashRegistry


@admin.register(TrashRegistry)
class TrashRegistryAdmin(admin.ModelAdmin):
    """Admin configuration for TrashRegistry model."""
    
    list_display = [
        'title', 'model_name', 'trashed_by', 
        'days_until_expiry_display', 'status_display', 'created_at'
    ]
    list_filter = ['model_name', 'created_at', 'expires_at']
    search_fields = ['title', 'subtitle', 'trashed_by__email']
    readonly_fields = [
        'content_type', 'object_id', 'created_at', 
        'updated_at', 'days_until_expiry', 'is_expired'
    ]
    raw_id_fields = ['trashed_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Item', {
            'fields': ('title', 'subtitle', 'icon', 'model_name', 'model_verbose_name')
        }),
        ('Source Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Trash Info', {
            'fields': ('trashed_by', 'trash_reason', 'expires_at')
        }),
        ('Original Data', {
            'fields': ('original_data',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('days_until_expiry', 'is_expired', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def days_until_expiry_display(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return '-'
        if days == 0:
            return format_html('<span style="color: red;">Expired</span>')
        if days <= 7:
            return format_html('<span style="color: orange;">{} days</span>', days)
        return f'{days} days'
    days_until_expiry_display.short_description = 'Expires In'
    
    def status_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">⚠ Expired</span>')
        return format_html('<span style="color: green;">● Active</span>')
    status_display.short_description = 'Status'
    
    actions = ['restore_selected', 'delete_permanently', 'empty_expired']
    
    @admin.action(description='Restore selected items')
    def restore_selected(self, request, queryset):
        restored = 0
        failed = 0
        
        for item in queryset:
            try:
                if item.restore():
                    restored += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        
        if restored:
            self.message_user(request, f'{restored} items restored.')
        if failed:
            self.message_user(request, f'{failed} items could not be restored.', level='warning')
    
    @admin.action(description='Permanently delete selected items')
    def delete_permanently(self, request, queryset):
        count = 0
        for item in queryset:
            try:
                item.permanent_delete()
                count += 1
            except Exception:
                pass
        self.message_user(request, f'{count} items permanently deleted.')
    
    @admin.action(description='Delete all expired items')
    def empty_expired(self, request, queryset):
        from django.utils import timezone
        expired = TrashRegistry.objects.filter(expires_at__lte=timezone.now())
        count = 0
        for item in expired:
            try:
                item.permanent_delete()
                count += 1
            except Exception:
                pass
        self.message_user(request, f'{count} expired items deleted.')
