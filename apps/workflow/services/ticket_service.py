from decimal import Decimal
from typing import List
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

from apps.core.services.base import BaseService, service_action
from apps.workflow.models import (
    Ticket, TicketActivity, AgentProfile, Department
)


class TicketService(BaseService):
    """
    Service for managing tickets.
    """
    
    model = Ticket
    
    # SLA hours by priority
    SLA_HOURS = {
        'urgent': 4,
        'high': 8,
        'medium': 24,
        'low': 48,
    }
    
    @service_action(audit=True)
    def create_ticket(
        self,
        ticket_type: str,
        subject: str,
        description: str = '',
        priority: str = 'medium',
        customer=None,
        linked_object=None,
        estimated_amount: float = 0,
        required_department: Department = None,
        auto_assign: bool = True
    ) -> Ticket:
        """
        Create a new ticket with optional auto-assignment.
        """
        from apps.workflow.services import AssignmentService
        
        # Calculate SLA due time
        sla_hours = self.SLA_HOURS.get(priority, 24)
        sla_due_at = timezone.now() + timedelta(hours=sla_hours)
        
        # Get content type for linked object
        content_type = None
        object_id = None
        if linked_object:
            content_type = ContentType.objects.get_for_model(linked_object)
            object_id = str(linked_object.pk)
        
        # Create ticket
        ticket = self.create(
            ticket_type=ticket_type,
            subject=subject,
            description=description,
            priority=priority,
            customer=customer,
            content_type=content_type,
            object_id=object_id,
            estimated_amount=Decimal(str(estimated_amount)),
            required_department=required_department,
            sla_due_at=sla_due_at
        )
        
        # Log creation
        TicketActivity.objects.create(
            ticket=ticket,
            activity_type='created',
            performed_by=self._current_user,
            details={
                'priority': priority,
                'type': ticket_type,
                'amount': str(estimated_amount)
            }
        )
        
        # Auto-assign if requested
        if auto_assign:
            assignment_service = AssignmentService(user=self._current_user)
            assignment_service.auto_assign_ticket(ticket)
        
        return ticket
    
    def get_available_tickets(self, agent: AgentProfile) -> List[Ticket]:
        """
        Get tickets that an agent can pick.
        """
        from django.db.models import Q
        
        # Base query: unassigned, open tickets
        queryset = self.model.objects.filter(
            status__in=['open', 'escalated'],
            assigned_to__isnull=True
        )
        
        # Filter by agent's max level
        max_level = agent.max_level
        queryset = queryset.filter(required_workclass_level__lte=max_level)
        
        # Filter by department if agent has one
        if agent.department:
            queryset = queryset.filter(
                Q(required_department__isnull=True) |
                Q(required_department=agent.department)
            )
        
        # Order by priority and age
        priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
        return sorted(
            queryset,
            key=lambda t: (priority_order.get(t.priority, 2), t.created_at)
        )
    
    def get_agent_queue(self, agent: AgentProfile) -> List[Ticket]:
        """
        Get tickets assigned to an agent.
        """
        return self.model.objects.filter(
            assigned_to=agent,
            status__in=['assigned', 'in_progress', 'pending_customer', 'pending_approval']
        ).order_by('sla_due_at')
    
    @service_action(audit=True)
    def add_note(self, ticket: Ticket, note: str) -> TicketActivity:
        """
        Add a note to a ticket.
        """
        activity = TicketActivity.objects.create(
            ticket=ticket,
            activity_type='note',
            performed_by=self._current_user,
            note=note
        )
        ticket.save()  # Update timestamp
        return activity
    
    @service_action(audit=True)
    def resolve_ticket(self, ticket: Ticket, resolution_notes: str) -> Ticket:
        """
        Mark ticket as resolved.
        """
        ticket.resolve(resolution_notes, self._current_user)
        return ticket

    @service_action(audit=True)
    def change_status(self, ticket: Ticket, new_status: str, notes: str = ''):
        """
        Change ticket status with logging.
        """
        old_status = ticket.status
        
        updated_ticket = self.update(ticket, status=new_status)
        
        TicketActivity.objects.create(
            ticket=updated_ticket,
            activity_type='status_change',
            performed_by=self._current_user,
            note=notes,
            details={'from': old_status, 'to': new_status}
        )
        return updated_ticket
