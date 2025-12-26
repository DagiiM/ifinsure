"""
Admin configuration for workflow models.
"""
from decimal import Decimal
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from apps.workflow.models import (
    Department, WorkClass, AgentProfile, Ticket, 
    TicketActivity, AgentPerformance
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']
    actions = ['create_default_departments']
    
    @admin.action(description='⚡ Create Default Departments')
    def create_default_departments(self, request, queryset):
        """Create standard insurance departments."""
        defaults = [
            ('SALES', 'Sales & Distribution', 'New policy sales and distribution'),
            ('UNDERWRITING', 'Underwriting', 'Policy underwriting and risk assessment'),
            ('CLAIMS', 'Claims Processing', 'Claims submission and processing'),
            ('SUPPORT', 'Customer Support', 'Customer service and support'),
            ('BILLING', 'Billing & Finance', 'Billing, payments, and finance'),
        ]
        created = 0
        for code, name, desc in defaults:
            obj, was_created = Department.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc}
            )
            if was_created:
                created += 1
        self.message_user(
            request,
            f'Created {created} departments. {len(defaults) - created} already existed.',
            messages.SUCCESS
        )


@admin.register(WorkClass)
class WorkClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'level_display', 'department', 'monetary_limit_display', 'daily_ticket_limit', 'is_active']
    list_filter = ['level', 'department', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['level', 'name']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['create_preset_workclasses']
    
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'level', 'department', 'description')
        }),
        ('Authorization', {
            'fields': ('monetary_limit', 'permissions')
        }),
        ('Settings', {
            'fields': ('daily_ticket_limit', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def level_display(self, obj):
        colors = {1: '#9ca3af', 2: '#60a5fa', 3: '#34d399', 4: '#f59e0b', 5: '#ef4444'}
        return format_html(
            '<span style="padding: 2px 8px; border-radius: 4px; background: {}; color: white; font-weight: 600;">L{}</span>',
            colors.get(obj.level, '#6b7280'),
            obj.level
        )
    level_display.short_description = 'Level'
    level_display.admin_order_field = 'level'
    
    def monetary_limit_display(self, obj):
        return f"KES {obj.monetary_limit:,.0f}"
    monetary_limit_display.short_description = 'Monetary Limit'
    
    @admin.action(description='⚡ Create Preset WorkClasses (All Levels)')
    def create_preset_workclasses(self, request, queryset):
        """
        Create standard industry WorkClasses for quick system setup.
        This significantly reduces CES for admin staff.
        """
        presets = [
            # Level 1 - Trainee
            {
                'code': 'TRAINEE',
                'name': 'Trainee Agent',
                'level': 1,
                'monetary_limit': Decimal('10000'),
                'daily_ticket_limit': 5,
                'description': 'New trainees under supervision. Limited access.',
                'permissions': {'view_tickets': True, 'create_tickets': False}
            },
            # Level 2 - Junior
            {
                'code': 'AGENT_L2',
                'name': 'Junior Agent',
                'level': 2,
                'monetary_limit': Decimal('50000'),
                'daily_ticket_limit': 15,
                'description': 'Junior agents handling standard tasks.',
                'permissions': {'view_tickets': True, 'create_tickets': True, 'handle_claims': False}
            },
            {
                'code': 'SALES_L2',
                'name': 'Sales Agent',
                'level': 2,
                'monetary_limit': Decimal('100000'),
                'daily_ticket_limit': 20,
                'description': 'Sales focus - policy quotes and applications.',
                'permissions': {'view_tickets': True, 'create_policies': True}
            },
            # Level 3 - Agent
            {
                'code': 'AGENT_L3',
                'name': 'Agent',
                'level': 3,
                'monetary_limit': Decimal('200000'),
                'daily_ticket_limit': 20,
                'description': 'Full agent handling claims and policies.',
                'permissions': {'handle_claims': True, 'approve_small_claims': True}
            },
            {
                'code': 'CLAIMS_L3',
                'name': 'Claims Processor',
                'level': 3,
                'monetary_limit': Decimal('250000'),
                'daily_ticket_limit': 15,
                'description': 'Specialized claims processing.',
                'permissions': {'handle_claims': True, 'approve_claims': True}
            },
            {
                'code': 'SUPPORT_L3',
                'name': 'Support Specialist',
                'level': 3,
                'monetary_limit': Decimal('100000'),
                'daily_ticket_limit': 25,
                'description': 'Customer support specialist.',
                'permissions': {'handle_support': True, 'refunds': False}
            },
            # Level 4 - Senior
            {
                'code': 'SENIOR_L4',
                'name': 'Senior Agent',
                'level': 4,
                'monetary_limit': Decimal('500000'),
                'daily_ticket_limit': 15,
                'description': 'Senior agent with approval authority.',
                'permissions': {'approve_claims': True, 'approve_policies': True}
            },
            {
                'code': 'UNDERWRITER_L4',
                'name': 'Underwriter',
                'level': 4,
                'monetary_limit': Decimal('1000000'),
                'daily_ticket_limit': 10,
                'description': 'Policy underwriting and risk assessment.',
                'permissions': {'underwrite': True, 'approve_high_risk': True}
            },
            # Level 5 - Supervisor/Admin
            {
                'code': 'SUPERVISOR_L5',
                'name': 'Team Supervisor',
                'level': 5,
                'monetary_limit': Decimal('5000000'),
                'daily_ticket_limit': 10,
                'description': 'Team lead with full approval authority.',
                'permissions': {'full_access': True, 'manage_team': True}
            },
            {
                'code': 'ADMIN_L5',
                'name': 'Administrator',
                'level': 5,
                'monetary_limit': Decimal('10000000'),
                'daily_ticket_limit': 0,
                'description': 'System administrator with unlimited access.',
                'permissions': {'full_access': True, 'system_admin': True}
            },
        ]
        
        created = 0
        for preset in presets:
            code = preset.pop('code')
            obj, was_created = WorkClass.objects.get_or_create(
                code=code,
                defaults=preset
            )
            if was_created:
                created += 1
        
        self.message_user(
            request,
            f'✅ Created {created} WorkClasses. {len(presets) - created} already existed. '
            f'Agent staff can now be assigned roles immediately!',
            messages.SUCCESS
        )




@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'primary_workclass', 'department', 'current_load_display', 'is_available']
    list_filter = ['is_available', 'department', 'shift', 'primary_workclass']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'employee_id']
    raw_id_fields = ['user', 'supervisor']
    filter_horizontal = ['workclasses']
    readonly_fields = ['current_load', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'employee_id')
        }),
        ('Organization', {
            'fields': ('department', 'supervisor')
        }),
        ('Work Classes', {
            'fields': ('workclasses', 'primary_workclass')
        }),
        ('Capacity', {
            'fields': ('daily_capacity', 'current_load')
        }),
        ('Availability', {
            'fields': ('is_available', 'shift', 'shift_start', 'shift_end')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def current_load_display(self, obj):
        percentage = (obj.current_load / obj.daily_capacity * 100) if obj.daily_capacity > 0 else 0
        if percentage > 80:
            color = '#ef4444'
        elif percentage > 50:
            color = '#f59e0b'
        else:
            color = '#22c55e'
        return format_html(
            '<span style="color: {};">{} / {} ({:.0f}%)</span>',
            color, str(obj.current_load), str(obj.daily_capacity), percentage
        )
    current_load_display.short_description = 'Load'


class TicketActivityInline(admin.TabularInline):
    model = TicketActivity
    extra = 0
    readonly_fields = ['activity_type', 'performed_by', 'note', 'details', 'created_at']
    can_delete = False
    ordering = ['-created_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['reference', 'subject_short', 'ticket_type', 'priority_display', 'status_display', 'assigned_to', 'sla_status', 'created_at']
    list_filter = ['status', 'priority', 'ticket_type', 'required_department', 'created_at']
    search_fields = ['reference', 'subject', 'customer__email']
    raw_id_fields = ['customer', 'assigned_to', 'assigned_by', 'created_by']
    readonly_fields = ['reference', 'created_at', 'updated_at', 'assigned_at', 'first_response_at', 'resolved_at', 'closed_at']
    inlines = [TicketActivityInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Ticket', {
            'fields': ('reference', 'ticket_type', 'priority', 'status')
        }),
        ('Content', {
            'fields': ('subject', 'description')
        }),
        ('Customer', {
            'fields': ('customer',)
        }),
        ('Assignment', {
            'fields': ('required_workclass_level', 'required_department', 'estimated_amount', 'assigned_to', 'assigned_by', 'assigned_at')
        }),
        ('SLA', {
            'fields': ('sla_due_at', 'first_response_at', 'resolved_at', 'closed_at')
        }),
        ('Resolution', {
            'fields': ('resolution_notes',),
            'classes': ('collapse',)
        }),
        ('Linked Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def subject_short(self, obj):
        return obj.subject[:40] + '...' if len(obj.subject) > 40 else obj.subject
    subject_short.short_description = 'Subject'
    
    def priority_display(self, obj):
        colors = {
            'low': '#9ca3af',
            'medium': '#60a5fa',
            'high': '#f59e0b',
            'urgent': '#ef4444'
        }
        return format_html(
            '<span style="padding: 2px 8px; border-radius: 4px; background: {}; color: white; font-weight: 500; text-transform: uppercase; font-size: 11px;">{}</span>',
            colors.get(obj.priority, '#6b7280'),
            obj.priority
        )
    priority_display.short_description = 'Priority'
    priority_display.admin_order_field = 'priority'
    
    def status_display(self, obj):
        colors = {
            'open': '#60a5fa',
            'assigned': '#818cf8',
            'in_progress': '#a78bfa',
            'pending_customer': '#f59e0b',
            'pending_approval': '#f97316',
            'escalated': '#ef4444',
            'resolved': '#22c55e',
            'closed': '#6b7280',
            'cancelled': '#9ca3af'
        }
        return format_html(
            '<span style="padding: 2px 8px; border-radius: 4px; background: {}; color: white; font-weight: 500; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def sla_status(self, obj):
        if obj.status in ['resolved', 'closed', 'cancelled']:
            if obj.resolved_at and obj.sla_due_at:
                if obj.resolved_at <= obj.sla_due_at:
                    return format_html('<span style="color: #22c55e;">✓ Met</span>')
                else:
                    return format_html('<span style="color: #ef4444;">✗ Breached</span>')
            return format_html('<span style="color: #9ca3af;">—</span>')
        
        if obj.is_overdue:
            return format_html('<span style="color: #ef4444;">⚠ OVERDUE</span>')
        
        time_left = obj.time_to_sla
        if time_left:
            hours = time_left.total_seconds() / 3600
            if hours < 2:
                return format_html('<span style="color: #f59e0b;">{}h left</span>', float(hours))
            return format_html('<span style="color: #22c55e;">{}h left</span>', float(hours))
        return format_html('<span style="color: #9ca3af;">—</span>')
    sla_status.short_description = 'SLA'
    
    actions = ['assign_to_me', 'mark_resolved', 'escalate_tickets']
    
    @admin.action(description='📥 Assign to me')
    def assign_to_me(self, request, queryset):
        """Assign tickets to current user using AssignmentService."""
        from apps.workflow.services import AssignmentService
        
        try:
            agent = request.user.agent_profile
            count = 0
            for ticket in queryset.filter(assigned_to__isnull=True):
                if agent.can_handle_ticket(ticket):
                    try:
                        AssignmentService.assign_ticket(ticket, agent, assigned_by=request.user)
                        count += 1
                    except Exception as e:
                        self.message_user(request, f'Error assigning ticket {ticket.reference}: {e}', messages.WARNING)
            self.message_user(request, f'{count} tickets assigned to you.', messages.SUCCESS)
        except AgentProfile.DoesNotExist:
            self.message_user(request, 'You do not have an agent profile.', messages.ERROR)
    
    @admin.action(description='✅ Mark as resolved')
    def mark_resolved(self, request, queryset):
        """Resolve tickets using TicketService."""
        from apps.workflow.services import TicketService
        
        count = 0
        for ticket in queryset.filter(status__in=['assigned', 'in_progress']):
            try:
                TicketService.change_status(
                    ticket, 
                    'resolved', 
                    request.user, 
                    notes='Resolved via admin action'
                )
                count += 1
            except Exception as e:
                self.message_user(request, f'Error resolving ticket {ticket.reference}: {e}', messages.WARNING)
        self.message_user(request, f'{count} tickets marked as resolved.', messages.SUCCESS)
    
    @admin.action(description='⬆️ Escalate selected')
    def escalate_tickets(self, request, queryset):
        """Escalate tickets using TicketService."""
        from apps.workflow.services import TicketService
        
        count = 0
        for ticket in queryset.exclude(status__in=['resolved', 'closed', 'cancelled']):
            try:
                TicketService.change_status(
                    ticket, 
                    'escalated', 
                    request.user, 
                    notes='Escalated via admin action'
                )
                count += 1
            except Exception as e:
                self.message_user(request, f'Error escalating ticket {ticket.reference}: {e}', messages.WARNING)
        self.message_user(request, f'{count} tickets escalated.', messages.SUCCESS)


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'activity_type', 'performed_by', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['ticket__reference', 'performed_by__email']
    readonly_fields = ['ticket', 'activity_type', 'performed_by', 'details', 'note', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AgentPerformance)
class AgentPerformanceAdmin(admin.ModelAdmin):
    list_display = ['agent', 'period_type', 'period_start', 'tickets_resolved', 'resolution_rate', 'sla_compliance_rate', 'policies_sold', 'total_premium_value']
    list_filter = ['period_type', 'period_start', 'agent__department']
    search_fields = ['agent__user__email', 'agent__employee_id']
    date_hierarchy = 'period_start'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Agent & Period', {
            'fields': ('agent', 'period_type', 'period_start', 'period_end')
        }),
        ('Ticket Metrics', {
            'fields': ('tickets_assigned', 'tickets_resolved', 'tickets_escalated', 'tickets_reopened')
        }),
        ('Time Metrics', {
            'fields': ('avg_resolution_time', 'avg_first_response_time', 'total_work_time')
        }),
        ('SLA', {
            'fields': ('sla_met', 'sla_breached')
        }),
        ('Sales', {
            'fields': ('policies_sold', 'total_premium_value', 'leads_handled', 'leads_converted')
        }),
        ('Claims', {
            'fields': ('claims_approved', 'claims_rejected', 'total_claims_value')
        }),
        ('Customer Satisfaction', {
            'fields': ('csat_responses', 'csat_total_score')
        }),
    )
