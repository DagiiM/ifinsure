from django.contrib import admin
from django.contrib import messages
from django.db import models
from apps.integrations.models import (
    IntegrationCategory, IntegrationProvider, 
    IntegrationConfig, IntegrationLog, WebhookEvent
)


@admin.register(IntegrationCategory)
class IntegrationCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'display_order', 'provider_count', 'active_count']
    list_filter = ['is_active']
    list_editable = ['display_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order']


@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_available', 'supports_webhooks', 'supports_sandbox']
    list_filter = ['category', 'is_available', 'supports_webhooks']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'slug', 'description', 'logo')
        }),
        ('URLs', {
            'fields': ('website_url', 'documentation_url')
        }),
        ('Technical', {
            'fields': ('provider_class', 'config_schema')
        }),
        ('Features', {
            'fields': ('supports_webhooks', 'supports_sandbox', 'supports_refunds')
        }),
        ('Availability', {
            'fields': ('is_available', 'is_active', 'countries')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'environment', 'is_enabled', 'is_primary', 'last_test_status']
    list_filter = ['provider__category', 'environment', 'is_enabled', 'is_primary']
    search_fields = ['name', 'provider__name']
    readonly_fields = ['created_at', 'updated_at', 'last_tested_at', 'last_test_status', 'last_test_message']
    
    fieldsets = (
        (None, {
            'fields': ('provider', 'name', 'environment')
        }),
        ('Status', {
            'fields': ('is_enabled', 'is_primary')
        }),
        ('Credentials', {
            'fields': ('credentials',),
            'classes': ('collapse',),
            'description': 'Warning: Credentials are sensitive. Handle with care.'
        }),
        ('Webhooks', {
            'fields': ('webhook_url', 'webhook_secret'),
            'classes': ('collapse',)
        }),
        ('Testing', {
            'fields': ('last_tested_at', 'last_test_status', 'last_test_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['test_connections', 'enable_configs', 'disable_configs']
    
    @admin.action(description='🔗 Test selected configurations')
    def test_connections(self, request, queryset):
        """Test configurations using IntegrationService."""
        from apps.integrations.services import IntegrationService
        
        success_count = 0
        for config in queryset:
            try:
                result = IntegrationService.test_connection(config)
                if result.get('success'):
                    success_count += 1
            except Exception as e:
                self.message_user(request, f'Error testing {config.name}: {e}', messages.WARNING)
        
        self.message_user(
            request,
            f'Tested {queryset.count()} configurations. {success_count} successful.',
            messages.SUCCESS
        )
    
    @admin.action(description='✅ Enable selected configurations')
    def enable_configs(self, request, queryset):
        """Enable configurations using IntegrationService."""
        from apps.integrations.services import IntegrationService
        
        count = 0
        for config in queryset:
            try:
                IntegrationService.update_config(config, updated_by=request.user, is_enabled=True)
                count += 1
            except Exception as e:
                self.message_user(request, f'Error enabling {config.name}: {e}', messages.WARNING)
        self.message_user(request, f'Enabled {count} configurations.', messages.SUCCESS)
    
    @admin.action(description='⛔ Disable selected configurations')
    def disable_configs(self, request, queryset):
        """Disable configurations using IntegrationService."""
        from apps.integrations.services import IntegrationService
        
        count = 0
        for config in queryset:
            try:
                IntegrationService.update_config(config, updated_by=request.user, is_enabled=False)
                count += 1
            except Exception as e:
                self.message_user(request, f'Error disabling {config.name}: {e}', messages.WARNING)
        self.message_user(request, f'Disabled {count} configurations.', messages.SUCCESS)


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'config', 'action', 'status', 'response_time_ms', 'reference_id']
    list_filter = ['status', 'config__provider', 'action', 'created_at']
    search_fields = ['action', 'reference_id', 'error_message']
    readonly_fields = [
        'config', 'action', 'request_data', 'response_data', 
        'status', 'error_message', 'response_time_ms',
        'reference_type', 'reference_id', 'ip_address', 
        'user_agent', 'created_at'
    ]
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'config', 'event_type', 'status', 'retry_count', 'processed_at']
    list_filter = ['status', 'config__provider', 'created_at']
    search_fields = ['event_type', 'error_message']
    readonly_fields = [
        'config', 'event_type', 'payload', 'headers',
        'status', 'error_message', 'processed_at',
        'retry_count', 'ip_address', 'created_at'
    ]
    date_hierarchy = 'created_at'
    
    actions = ['reprocess_events']
    
    @admin.action(description='🔄 Reprocess selected events')
    def reprocess_events(self, request, queryset):
        """Queue events for reprocessing."""
        count = queryset.filter(
            status__in=['failed', 'pending']
        ).update(
            status='pending',
            retry_count=models.F('retry_count') + 1
        )
        self.message_user(request, f'Queued {count} events for reprocessing.', messages.SUCCESS)
