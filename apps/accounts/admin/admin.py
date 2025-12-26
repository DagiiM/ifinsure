"""
Accounts admin configuration with enhanced staff management.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from django.utils.html import format_html
from apps.accounts.models import User, Profile


class ProfileInline(admin.StackedInline):
    """Inline profile in user admin."""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class AgentProfileInline(admin.StackedInline):
    """Inline agent profile for quick workclass assignment."""
    model = None  # Set dynamically to avoid import issues
    can_delete = False
    verbose_name_plural = 'Agent/Staff Settings'
    fk_name = 'user'
    extra = 0
    
    fieldsets = (
        ('Work Assignment', {
            'fields': ('employee_id', 'department', 'primary_workclass', 'workclasses'),
            'classes': ('collapse',),
        }),
        ('Capacity & Availability', {
            'fields': ('daily_capacity', 'current_load', 'is_available', 'shift'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('department', 'primary_workclass')


# Try to import AgentProfile for inline
try:
    from apps.workflow.models import AgentProfile
    AgentProfileInline.model = AgentProfile
    HAS_WORKFLOW = True
except ImportError:
    HAS_WORKFLOW = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced user admin with quick role setup actions."""
    inlines = [ProfileInline]
    
    # Add AgentProfileInline if workflow app is available
    def get_inlines(self, request, obj=None):
        inlines = [ProfileInline]
        if HAS_WORKFLOW and obj and obj.user_type in ['agent', 'staff', 'admin']:
            inlines.append(AgentProfileInline)
        return inlines
    
    list_display = ['email', 'first_name', 'last_name', 'user_type_badge', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    actions = ['make_agent', 'make_staff', 'make_customer', 'quick_setup_agent']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'date_of_birth')}),
        ('Address', {'fields': ('address', 'city', 'country')}),
        ('Permissions', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'user_type', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def user_type_badge(self, obj):
        """Display user type with color badge."""
        colors = {
            'customer': '#6b7280',
            'agent': '#2563eb',
            'staff': '#7c3aed',
            'admin': '#dc2626',
        }
        color = colors.get(obj.user_type, '#6b7280')
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; background: {}; color: white; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.get_user_type_display()
        )
    user_type_badge.short_description = 'Role'
    user_type_badge.admin_order_field = 'user_type'
    
    # ========== ADMIN ACTIONS ==========
    
    @admin.action(description='🔷 Set as Agent')
    def make_agent(self, request, queryset):
        """Quickly convert selected users to agent role using AccountService."""
        from apps.accounts.services import AccountService
        
        count = 0
        for user in queryset:
            try:
                AccountService.change_user_type(user, 'agent', request.user)
                count += 1
            except ValueError as e:
                self.message_user(request, str(e), messages.ERROR)
        
        self.message_user(
            request,
            f'{count} user(s) set as Agent. AgentProfiles created automatically.',
            messages.SUCCESS
        )
    
    @admin.action(description='🟣 Set as Staff')
    def make_staff(self, request, queryset):
        """Quickly convert selected users to staff role using AccountService."""
        from apps.accounts.services import AccountService
        
        count = 0
        for user in queryset:
            try:
                AccountService.change_user_type(user, 'staff', request.user)
                count += 1
            except ValueError as e:
                self.message_user(request, str(e), messages.ERROR)
        
        self.message_user(
            request,
            f'{count} user(s) set as Staff. AgentProfiles created automatically.',
            messages.SUCCESS
        )
    
    @admin.action(description='⚪ Set as Customer')
    def make_customer(self, request, queryset):
        """Quickly convert selected users to customer role using AccountService."""
        from apps.accounts.services import AccountService
        
        count = 0
        for user in queryset:
            try:
                AccountService.change_user_type(user, 'customer', request.user)
                count += 1
            except ValueError as e:
                self.message_user(request, str(e), messages.ERROR)
        
        self.message_user(
            request,
            f'{count} user(s) set as Customer.',
            messages.SUCCESS
        )
    
    @admin.action(description='⚡ Quick Setup: Agent with Default WorkClass')
    def quick_setup_agent(self, request, queryset):
        """
        One-click agent setup:
        1. Set user_type to agent
        2. Create AgentProfile
        3. Assign default WorkClass (Level 2 - Junior Agent)
        """
        if not HAS_WORKFLOW:
            self.message_user(
                request,
                'Workflow app not available. Cannot assign WorkClass.',
                messages.ERROR
            )
            return
        
        from apps.workflow.models import WorkClass
        
        # Find or create default workclass
        default_workclass, created = WorkClass.objects.get_or_create(
            code='AGENT_L2',
            defaults={
                'name': 'Junior Agent',
                'level': 2,
                'description': 'Default workclass for new agents',
                'monetary_limit': 50000,
                'daily_ticket_limit': 15,
            }
        )
        
        count = 0
        for user in queryset:
            user.user_type = 'agent'
            user.is_staff = True
            user.save()
            
            # AgentProfile is auto-created by signal
            if hasattr(user, 'agent_profile'):
                user.agent_profile.primary_workclass = default_workclass
                user.agent_profile.workclasses.add(default_workclass)
                user.agent_profile.is_available = True
                user.agent_profile.save()
                count += 1
        
        self.message_user(
            request,
            f'{count} user(s) set up as agents with "{default_workclass.name}" workclass. They can start working now!',
            messages.SUCCESS
        )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Profile admin."""
    list_display = ['user', 'id_type', 'id_number', 'occupation', 'created_at']
    list_filter = ['id_type', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'id_number']
    raw_id_fields = ['user']
