"""
Base Admin - Common functionality for all admin classes.

Provides:
- Consistent UI/UX patterns
- Standard actions (activate/deactivate, export)
- Audit logging integration
- Performance optimizations
- Enhanced list display
"""
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponse
import csv


class BaseAdmin(admin.ModelAdmin):
    """
    Enhanced base admin class with common functionality.
    
    Features:
    - Automatic readonly timestamps
    - Common actions (activate, deactivate, export)
    - Status badges for boolean and choice fields
    - Audit logging integration
    - Query optimization
    - CSV export
    
    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(BaseAdmin):
            list_display = ['name', 'status_badge', 'is_active_badge', 'created_at']
            list_filter = ['status', 'is_active']
    """
    
    # ==================== Display Settings ====================
    
    # Items per page
    list_per_page = 25
    
    # Show count in list view
    show_full_result_count = True
    
    # Date hierarchy (override in subclass)
    date_hierarchy = None
    
    # Save buttons on top
    save_on_top = True
    
    # ==================== Readonly Fields ====================
    
    # Fields that are always readonly
    base_readonly_fields = ['created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        """Add base readonly fields to any defined in subclass."""
        readonly = list(super().get_readonly_fields(request, obj))
        
        for field in self.base_readonly_fields:
            if hasattr(self.model, field) and field not in readonly:
                readonly.append(field)
        
        return readonly
    
    # ==================== Query Optimization ====================
    
    # Fields to select_related (override in subclass)
    list_select_related = []
    
    def get_queryset(self, request):
        """Optimize queries with select_related."""
        qs = super().get_queryset(request)
        if self.list_select_related:
            qs = qs.select_related(*self.list_select_related)
        return qs
    
    # ==================== Common Actions ====================
    
    actions = ['activate_selected', 'deactivate_selected', 'export_as_csv']
    
    @admin.action(description='✅ Activate selected')
    def activate_selected(self, request, queryset):
        """Activate selected items (set is_active=True)."""
        if not hasattr(self.model, 'is_active'):
            self.message_user(request, 'This model does not support activation.', messages.ERROR)
            return
        
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f'{count} item(s) activated.', messages.SUCCESS)
    
    @admin.action(description='⛔ Deactivate selected')
    def deactivate_selected(self, request, queryset):
        """Deactivate selected items (set is_active=False)."""
        if not hasattr(self.model, 'is_active'):
            self.message_user(request, 'This model does not support deactivation.', messages.ERROR)
            return
        
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f'{count} item(s) deactivated.', messages.SUCCESS)
    
    @admin.action(description='📊 Export selected as CSV')
    def export_as_csv(self, request, queryset):
        """Export selected items as CSV."""
        meta = self.model._meta
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.model_name}_export.csv'
        
        writer = csv.writer(response)
        
        # Get field names
        field_names = [field.name for field in meta.fields]
        writer.writerow(field_names)
        
        # Write data
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif hasattr(value, 'pk'):
                    value = str(value)
                row.append(value)
            writer.writerow(row)
        
        return response
    
    # ==================== Badge Helpers ====================
    
    def is_active_badge(self, obj):
        """Display is_active as colored badge."""
        if not hasattr(obj, 'is_active'):
            return '-'
        
        if obj.is_active:
            return format_html(
                '<span style="padding: 3px 8px; border-radius: 4px; '
                'background: #22c55e; color: white; font-size: 11px; font-weight: 600;">Active</span>'
            )
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; '
            'background: #ef4444; color: white; font-size: 11px; font-weight: 600;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def get_status_badge(self, value, color_map=None):
        """
        Create colored badge for status fields.
        
        Args:
            value: The status value
            color_map: Dict mapping values to colors
            
        Returns:
            HTML span with colored badge
        """
        default_colors = {
            'active': '#22c55e',
            'inactive': '#ef4444',
            'pending': '#f59e0b',
            'approved': '#22c55e',
            'rejected': '#ef4444',
            'draft': '#6b7280',
            'published': '#22c55e',
            'completed': '#22c55e',
            'cancelled': '#9ca3af',
            'processing': '#3b82f6',
        }
        
        colors = color_map or default_colors
        color = colors.get(str(value).lower(), '#6b7280')
        
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; '
            'background: {}; color: white; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            str(value).replace('_', ' ').title()
        )
    
    def get_boolean_badge(self, value, true_label='Yes', false_label='No'):
        """Create colored badge for boolean fields."""
        if value:
            return format_html(
                '<span style="padding: 3px 8px; border-radius: 4px; '
                'background: #22c55e; color: white; font-size: 11px; font-weight: 600;">{}</span>',
                true_label
            )
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; '
            'background: #ef4444; color: white; font-size: 11px; font-weight: 600;">{}</span>',
            false_label
        )
    
    def get_priority_badge(self, priority, priorities=None):
        """Create colored badge for priority fields."""
        default_priorities = {
            'low': ('#9ca3af', '🔵'),
            'medium': ('#60a5fa', '🟡'),
            'high': ('#f59e0b', '🟠'),
            'urgent': ('#ef4444', '🔴'),
            'critical': ('#dc2626', '⚠️'),
        }
        
        priority_map = priorities or default_priorities
        color, icon = priority_map.get(str(priority).lower(), ('#6b7280', '●'))
        
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; '
            'background: {}; color: white; font-size: 11px; font-weight: 600;">{} {}</span>',
            color,
            icon,
            str(priority).title()
        )
    
    # ==================== Utility Methods ====================
    
    def truncate_text(self, text, length=50):
        """Truncate text to specified length."""
        if not text:
            return '-'
        return text[:length] + '...' if len(text) > length else text
    
    def format_currency(self, amount, currency='KES'):
        """Format amount as currency."""
        if amount is None:
            return '-'
        return f'{currency} {amount:,.2f}'
    
    def format_date(self, dt):
        """Format datetime for display."""
        if not dt:
            return '-'
        return dt.strftime('%b %d, %Y %H:%M')
    
    def time_since(self, dt):
        """Display time since date."""
        if not dt:
            return '-'
        
        delta = timezone.now() - dt
        
        if delta.days > 365:
            years = delta.days // 365
            return f'{years}y ago'
        if delta.days > 30:
            months = delta.days // 30
            return f'{months}mo ago'
        if delta.days > 0:
            return f'{delta.days}d ago'
        
        hours = delta.seconds // 3600
        if hours > 0:
            return f'{hours}h ago'
        
        minutes = delta.seconds // 60
        return f'{minutes}m ago' if minutes > 0 else 'just now'
    
    # ==================== Save Hooks ====================
    
    def save_model(self, request, obj, form, change):
        """Set modified_by on save if model supports it."""
        if hasattr(obj, 'modified_by'):
            obj.modified_by = request.user
        
        if not change and hasattr(obj, 'created_by') and not obj.created_by:
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)


class ReadOnlyAdmin(BaseAdmin):
    """
    Admin class for read-only models (logs, audit trails, etc).
    """
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    # Remove modification actions
    actions = ['export_as_csv']


class AuditableAdmin(BaseAdmin):
    """
    Admin with full audit trail integration.
    Shows who created/modified and when.
    """
    
    base_readonly_fields = ['created_at', 'updated_at', 'created_by', 'modified_by']
    
    def get_fieldsets(self, request, obj=None):
        """Add audit fieldset."""
        fieldsets = list(super().get_fieldsets(request, obj))
        
        # Check if audit fieldset already exists
        for name, options in fieldsets:
            if name == 'Audit Information':
                return fieldsets
        
        # Add audit fieldset
        audit_fields = []
        for field in ['created_by', 'created_at', 'modified_by', 'updated_at']:
            if hasattr(self.model, field):
                audit_fields.append(field)
        
        if audit_fields:
            fieldsets.append(('Audit Information', {
                'fields': audit_fields,
                'classes': ('collapse',)
            }))
        
        return fieldsets
