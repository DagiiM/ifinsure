from typing import Optional, List
from django.db.models import Q, F

from apps.core.services.base import BaseService, service_action
from apps.workflow.models import Ticket, AgentProfile


class AssignmentService(BaseService):
    """
    Service for ticket assignment to agents.
    """
    
    model = AgentProfile
    
    @service_action(audit=True)
    def auto_assign_ticket(self, ticket: Ticket) -> Optional[AgentProfile]:
        """
        Auto-assign ticket to the best available agent.
        """
        # Find available agents
        available_agents = self.get_available_agents(ticket)
        
        if not available_agents:
            return None
        
        # Select agent with lowest load
        best_agent = min(available_agents, key=lambda a: a.current_load)
        
        # Assign
        ticket.assign_to_agent(best_agent, assigned_by=self._current_user)
        
        return best_agent
    
    def get_available_agents(self, ticket: Ticket) -> List[AgentProfile]:
        """
        Get agents who can handle a specific ticket.
        """
        agents = self.model.objects.filter(
            is_active=True,
            is_available=True,
            current_load__lt=F('daily_capacity'),
            workclasses__level__gte=ticket.required_workclass_level
        ).distinct()
        
        # Filter by department
        if ticket.required_department:
            agents = agents.filter(
                Q(department__isnull=True) |
                Q(department=ticket.required_department)
            )
        
        # Filter by monetary limit if applicable
        if ticket.estimated_amount > 0:
            agents = agents.filter(
                workclasses__monetary_limit__gte=ticket.estimated_amount
            )
        
        return list(agents)
    
    @service_action(audit=True)
    def assign_ticket(self, ticket: Ticket, agent: AgentProfile) -> bool:
        """
        Manually assign a ticket to an agent.
        """
        if not agent.can_handle_ticket(ticket):
            return False
        
        ticket.assign_to_agent(agent, assigned_by=self._current_user)
        return True
    
    @service_action(audit=True)
    def pick_ticket(self, ticket: Ticket, agent: AgentProfile) -> bool:
        """
        Agent picks a ticket for themselves.
        """
        if not agent.can_handle_ticket(ticket):
            return False
        
        if ticket.assigned_to is not None:
            return False
        
        ticket.pick(agent)
        return True
    
    @service_action(audit=True)
    def escalate_ticket(self, ticket: Ticket, reason: str) -> bool:
        """
        Escalate a ticket to a higher level.
        """
        if ticket.required_workclass_level >= 5:
            return False  # Already at max level
        
        ticket.escalate(reason, self._current_user)
        
        # Try to auto-assign to available senior agent
        self.auto_assign_ticket(ticket)
        
        return True
