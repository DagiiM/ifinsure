"""
Workflow models for WorkClass-based agent management.
Inspired by Finacle's work distribution model.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from apps.core.models import BaseModel, SimpleBaseModel


class Department(BaseModel):
    """
    Organizational departments for work classification.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # is_active provided by BaseModel
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class WorkClass(BaseModel):
    """
    Work class defines the scope of operations an agent can perform.
    Each workclass has a level (1-5) indicating authority tier.
    """
    LEVEL_CHOICES = [
        (1, 'Level 1 - Trainee'),
        (2, 'Level 2 - Junior Agent'),
        (3, 'Level 3 - Agent'),
        (4, 'Level 4 - Senior Agent'),
        (5, 'Level 5 - Supervisor/Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    level = models.PositiveIntegerField(choices=LEVEL_CHOICES, default=2)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workclasses'
    )
    description = models.TextField(blank=True)
    
    # Authorization limits
    monetary_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Maximum amount this workclass can approve"
    )
    
    # Detailed permissions
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed permission flags"
    )
    
    # Settings
    daily_ticket_limit = models.PositiveIntegerField(
        default=20,
        help_text="Maximum tickets per day for agents in this class"
    )
    
    # is_active, created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Work Class'
        verbose_name_plural = 'Work Classes'
        ordering = ['level', 'name']
    
    def __str__(self):
        return f"{self.name} (L{self.level})"
    
    def has_permission(self, permission_key):
        """Check if this workclass has a specific permission."""
        return self.permissions.get(permission_key, False)
    
    def can_handle_amount(self, amount):
        """Check if this workclass can handle a given monetary amount."""
        if self.level == 5:  # Admin level can handle any amount
            return True
        return Decimal(str(amount)) <= self.monetary_limit


class AgentProfile(BaseModel):
    """
    Extended profile for agents with workclass assignments.
    """
    SHIFT_CHOICES = [
        ('morning', 'Morning (6AM - 2PM)'),
        ('afternoon', 'Afternoon (2PM - 10PM)'),
        ('night', 'Night (10PM - 6AM)'),
        ('flexible', 'Flexible'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_profile'
    )
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    # WorkClass assignments
    workclasses = models.ManyToManyField(
        WorkClass,
        related_name='agents',
        blank=True
    )
    primary_workclass = models.ForeignKey(
        WorkClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_agents'
    )
    
    # Organizational
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents'
    )
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members'
    )
    
    # Capacity
    daily_capacity = models.PositiveIntegerField(
        default=15,
        help_text="Maximum tickets this agent can handle per day"
    )
    current_load = models.PositiveIntegerField(
        default=0,
        help_text="Current active tickets"
    )
    
    # Availability
    is_available = models.BooleanField(default=True)
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='flexible')
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)
    
    # Metadata
    # created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Agent Profile'
        verbose_name_plural = 'Agent Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} ({self.employee_id or 'No ID'})"
    
    @property
    def max_level(self):
        """Get the maximum workclass level for this agent."""
        if not self.workclasses.exists():
            return 0
        return self.workclasses.aggregate(models.Max('level'))['level__max'] or 0
    
    @property
    def max_monetary_limit(self):
        """Get the maximum monetary limit across all workclasses."""
        if not self.workclasses.exists():
            return Decimal('0.00')
        return self.workclasses.aggregate(models.Max('monetary_limit'))['monetary_limit__max'] or Decimal('0.00')
    
    def can_handle_ticket(self, ticket):
        """Check if agent can handle a specific ticket."""
        if not self.is_available:
            return False
        if self.current_load >= self.daily_capacity:
            return False
        if ticket.required_workclass_level > self.max_level:
            return False
        return True
    
    def increment_load(self):
        """Increment the agent's current load."""
        self.current_load += 1
        self.save(update_fields=['current_load'])
    
    def decrement_load(self):
        """Decrement the agent's current load."""
        if self.current_load > 0:
            self.current_load -= 1
            self.save(update_fields=['current_load'])


class Ticket(BaseModel):
    """
    Work ticket that can be assigned to agents.
    Uses generic relations to link to Claims, Policies, etc.
    """
    TYPE_CHOICES = [
        ('claim', 'Claim'),
        ('policy', 'Policy'),
        ('billing', 'Billing'),
        ('inquiry', 'General Inquiry'),
        ('complaint', 'Complaint'),
        ('renewal', 'Renewal'),
        ('endorsement', 'Endorsement'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending_customer', 'Pending Customer'),
        ('pending_approval', 'Pending Approval'),
        ('escalated', 'Escalated'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True, db_index=True, blank=True)
    
    # Type and Classification
    ticket_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Generic relation to linked entity (Claim, Policy, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.CharField(max_length=100, blank=True, null=True)
    linked_object = GenericForeignKey('content_type', 'object_id')
    
    # Requirements
    required_workclass_level = models.PositiveIntegerField(
        default=2,
        help_text="Minimum workclass level required"
    )
    required_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets'
    )
    estimated_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Estimated monetary value (for determining required level)"
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        AgentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Customer
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_tickets'
    )
    
    # Content
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # SLA Tracking
    sla_due_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # resolution
    resolution_notes = models.TextField(blank=True)
    
    # Escalation
    escalated_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalations'
    )
    escalation_reason = models.TextField(blank=True)
    
    # Metadata
    # created_by, created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['ticket_type', 'status']),
            models.Index(fields=['reference']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.subject[:50]}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        # Auto-calculate required level based on amount
        if self.estimated_amount > 0:
            self._set_required_level_from_amount()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_reference():
        """Generate unique ticket reference."""
        import random
        import string
        prefix = timezone.now().strftime('%Y%m%d')
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"TKT-{prefix}-{suffix}"
    
    def _set_required_level_from_amount(self):
        """Set required workclass level based on amount."""
        amount = float(self.estimated_amount)
        if amount > 500000:
            self.required_workclass_level = 5
        elif amount > 100000:
            self.required_workclass_level = 4
        elif amount > 50000:
            self.required_workclass_level = 3
        else:
            self.required_workclass_level = 2
    
    def assign_to_agent(self, agent, assigned_by=None):
        """Assign ticket to an agent."""
        self.assigned_to = agent
        self.assigned_by = assigned_by
        self.assigned_at = timezone.now()
        self.status = 'assigned'
        self.save()
        agent.increment_load()
        
        # Create activity
        TicketActivity.objects.create(
            ticket=self,
            activity_type='assigned',
            performed_by=assigned_by,
            details={'agent_id': str(agent.id), 'agent_name': str(agent)}
        )
    
    def pick(self, agent):
        """Agent picks this ticket (self-assignment)."""
        self.assign_to_agent(agent, assigned_by=agent.user)
    
    def escalate(self, reason, escalated_by):
        """Escalate ticket to higher level."""
        self.status = 'escalated'
        self.escalation_reason = reason
        self.required_workclass_level = min(self.required_workclass_level + 1, 5)
        
        # Unassign from current agent
        if self.assigned_to:
            self.assigned_to.decrement_load()
            self.assigned_to = None
            self.assigned_at = None
        
        self.save()
        
        TicketActivity.objects.create(
            ticket=self,
            activity_type='escalated',
            performed_by=escalated_by,
            details={'reason': reason, 'new_level': self.required_workclass_level}
        )
    
    def resolve(self, resolution_notes, resolved_by):
        """Mark ticket as resolved."""
        self.status = 'resolved'
        self.resolution_notes = resolution_notes
        self.resolved_at = timezone.now()
        self.save()
        
        if self.assigned_to:
            self.assigned_to.decrement_load()
        
        TicketActivity.objects.create(
            ticket=self,
            activity_type='resolved',
            performed_by=resolved_by,
            details={'notes': resolution_notes[:500]}
        )
    
    def close(self, closed_by):
        """Close the ticket."""
        self.status = 'closed'
        self.closed_at = timezone.now()
        self.save()
        
        TicketActivity.objects.create(
            ticket=self,
            activity_type='closed',
            performed_by=closed_by,
            details={}
        )
    
    @property
    def is_overdue(self):
        """Check if ticket is past SLA."""
        if not self.sla_due_at:
            return False
        return timezone.now() > self.sla_due_at and self.status not in ['resolved', 'closed', 'cancelled']
    
    @property
    def time_to_sla(self):
        """Get time remaining until SLA breach."""
        if not self.sla_due_at:
            return None
        return self.sla_due_at - timezone.now()


class TicketActivity(SimpleBaseModel):
    """
    Activity log for ticket actions.
    """
    ACTIVITY_TYPES = [
        ('created', 'Created'),
        ('assigned', 'Assigned'),
        ('picked', 'Picked'),
        ('status_change', 'Status Changed'),
        ('note', 'Note Added'),
        ('escalated', 'Escalated'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    details = models.JSONField(default=dict, blank=True)
    note = models.TextField(blank=True)
    # created_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Ticket Activity'
        verbose_name_plural = 'Ticket Activities'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ticket.reference} - {self.get_activity_type_display()}"


class AgentPerformance(SimpleBaseModel):
    """
    Agent performance metrics for a given period.
    """
    PERIOD_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        AgentProfile,
        on_delete=models.CASCADE,
        related_name='performance_records'
    )
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES, default='daily')
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Ticket metrics
    tickets_assigned = models.PositiveIntegerField(default=0)
    tickets_resolved = models.PositiveIntegerField(default=0)
    tickets_escalated = models.PositiveIntegerField(default=0)
    tickets_reopened = models.PositiveIntegerField(default=0)
    
    # Time Metrics (in minutes)
    avg_resolution_time = models.PositiveIntegerField(default=0)
    avg_first_response_time = models.PositiveIntegerField(default=0)
    total_work_time = models.PositiveIntegerField(default=0)
    
    # SLA
    sla_met = models.PositiveIntegerField(default=0)
    sla_breached = models.PositiveIntegerField(default=0)
    
    # Sales Metrics
    policies_sold = models.PositiveIntegerField(default=0)
    total_premium_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    leads_handled = models.PositiveIntegerField(default=0)
    leads_converted = models.PositiveIntegerField(default=0)
    
    # Claims Metrics
    claims_approved = models.PositiveIntegerField(default=0)
    claims_rejected = models.PositiveIntegerField(default=0)
    total_claims_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Customer Satisfaction
    csat_responses = models.PositiveIntegerField(default=0)
    csat_total_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # created_at, updated_at provided by BaseModel
    
    class Meta:
        verbose_name = 'Agent Performance'
        verbose_name_plural = 'Agent Performance Records'
        ordering = ['-period_start']
        unique_together = ['agent', 'period_type', 'period_start']
    
    def __str__(self):
        return f"{self.agent} - {self.period_type} ({self.period_start})"
    
    @property
    def resolution_rate(self):
        """Calculate ticket resolution rate."""
        if self.tickets_assigned == 0:
            return 0
        return round((self.tickets_resolved / self.tickets_assigned) * 100, 1)
    
    @property
    def sla_compliance_rate(self):
        """Calculate SLA compliance percentage."""
        total = self.sla_met + self.sla_breached
        if total == 0:
            return 100
        return round((self.sla_met / total) * 100, 1)
    
    @property
    def conversion_rate(self):
        """Calculate lead conversion rate."""
        if self.leads_handled == 0:
            return 0
        return round((self.leads_converted / self.leads_handled) * 100, 1)
    
    @property
    def avg_csat_score(self):
        """Calculate average customer satisfaction score."""
        if self.csat_responses == 0:
            return 0
        return round(float(self.csat_total_score) / self.csat_responses, 2)
