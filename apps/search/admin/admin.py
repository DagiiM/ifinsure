"""
Search admin configuration.
"""
from django.contrib import admin
from django.utils.html import format_html
from ..models import SearchIndex, SearchHistory


@admin.register(SearchIndex)
class SearchIndexAdmin(admin.ModelAdmin):
    """Admin configuration for SearchIndex model."""
    
    list_display = [
        'title', 'model_name', 'visibility', 
        'weight', 'has_url', 'created_at'
    ]
    list_filter = ['model_name', 'visibility', 'created_at']
    search_fields = ['title', 'subtitle', 'content', 'keywords']
    readonly_fields = ['created_at', 'updated_at', 'content_type', 'object_id']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'subtitle', 'content', 'keywords')
        }),
        ('Source Object', {
            'fields': ('content_type', 'object_id', 'model_name', 'model_verbose_name')
        }),
        ('Display', {
            'fields': ('icon', 'url', 'weight')
        }),
        ('Access Control', {
            'fields': ('visibility', 'owner_id')
        }),
        ('Extra Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_url(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">View</a>', obj.url)
        return '-'
    has_url.short_description = 'URL'
    
    actions = ['rebuild_selected', 'delete_selected_with_cleanup']
    
    @admin.action(description='Rebuild index for selected entries')
    def rebuild_selected(self, request, queryset):
        from ..services import IndexerService
        indexer = IndexerService()
        count = 0
        
        for entry in queryset:
            try:
                obj = entry.content_object
                if obj:
                    indexer.index_object(obj)
                    count += 1
            except Exception as e:
                self.message_user(request, f'Error reindexing {entry}: {e}', level='error')
        
        self.message_user(request, f'{count} entries reindexed.')


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for SearchHistory model."""
    
    list_display = [
        'query', 'user', 'results_count', 
        'search_duration_ms', 'has_click', 'created_at'
    ]
    list_filter = ['created_at', 'results_count']
    search_fields = ['query', 'user__email', 'user__first_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Search', {
            'fields': ('user', 'query', 'results_count', 'search_duration_ms')
        }),
        ('Filters', {
            'fields': ('filters_used',),
            'classes': ('collapse',)
        }),
        ('Click Data', {
            'fields': ('clicked_result_id', 'clicked_result_type'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_click(self, obj):
        return bool(obj.clicked_result_id)
    has_click.boolean = True
    has_click.short_description = 'Clicked'
