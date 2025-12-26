from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseDetailView,
    StaffRequiredMixin
)
from apps.workflow.models import Ticket, TicketActivity, AgentProfile
from apps.workflow.services import TicketService, AssignmentService, PerformanceService


class AgentRequiredMixin(LoginRequiredMixin):
    """Mixin that requires user to have an agent profile."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        try:
            self.agent = request.user.agent_profile
        except AgentProfile.DoesNotExist:
            messages.error(request, 'You do not have an agent profile.')
            return redirect('dashboard:home')
        
        return super().dispatch(request, *args, **kwargs)


class AgentDashboardView(AgentRequiredMixin, BaseTemplateView):
    """Main agent dashboard."""
    template_name = 'workflow/agent_dashboard.html'
    page_title = 'Agent Dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent = self.agent
        
        ticket_service = self.get_service(TicketService)
        perf_service = self.get_service(PerformanceService)
        
        # My queue
        context['my_queue'] = ticket_service.get_agent_queue(agent)[:10]
        context['queue_count'] = Ticket.objects.filter(
            assigned_to=agent,
            status__in=['assigned', 'in_progress', 'pending_customer', 'pending_approval']
        ).count()
        
        # Available tickets
        available_tickets = ticket_service.get_available_tickets(agent)
        context['available_tickets'] = available_tickets[:10]
        context['available_count'] = len(available_tickets)
        
        # Recent activity
        context['recent_activity'] = TicketActivity.objects.filter(
            Q(ticket__assigned_to=agent) | Q(performed_by=self.request.user)
        ).select_related('ticket', 'performed_by').order_by('-created_at')[:10]
        
        # Stats
        context['agent'] = agent
        context['stats'] = perf_service.get_agent_stats(agent, days=30)
        
        # Today's metrics
        context['today'] = perf_service.get_or_create_daily_performance(agent)
        
        # Overdue
        context['overdue_count'] = Ticket.objects.filter(
            assigned_to=agent,
            status__in=['assigned', 'in_progress'],
            sla_due_at__lt=timezone.now()
        ).count()
        
        return context


class MyQueueView(AgentRequiredMixin, BaseListView):
    """List of tickets assigned to current agent."""
    template_name = 'workflow/my_queue.html'
    context_object_name = 'tickets'
    page_title = 'My Queue'
    
    def get_queryset(self):
        return Ticket.objects.filter(
            assigned_to=self.agent,
            status__in=['assigned', 'in_progress', 'pending_customer', 'pending_approval']
        ).order_by('sla_due_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agent'] = self.agent
        return context


class AvailableTicketsView(AgentRequiredMixin, BaseListView):
    """List of tickets available for pickup."""
    template_name = 'workflow/available_tickets.html'
    context_object_name = 'tickets'
    page_title = 'Available Tickets'
    
    def get_queryset(self):
        ticket_service = self.get_service(TicketService)
        return ticket_service.get_available_tickets(self.agent)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agent'] = self.agent
        return context


class TicketDetailView(AgentRequiredMixin, BaseDetailView):
    """Ticket detail view with actions."""
    model = Ticket
    template_name = 'workflow/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_object(self):
        return get_object_or_404(Ticket, reference=self.kwargs['reference'])
    
    def get_page_title(self):
        return f"Ticket: {self.object.reference}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agent'] = self.agent
        context['activities'] = self.object.activities.select_related('performed_by').order_by('-created_at')
        context['can_pick'] = (
            self.object.assigned_to is None and 
            self.agent.can_handle_ticket(self.object)
        )
        context['can_resolve'] = (
            self.object.assigned_to == self.agent and
            self.agent.max_level >= 3
        )
        return context


class PickTicketView(AgentRequiredMixin, BaseView):
    """Pick a ticket for self-assignment."""
    
    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        assignment_service = self.get_service(AssignmentService)
        
        if assignment_service.pick_ticket(ticket, self.agent):
            messages.success(request, f'Ticket {ticket.reference} assigned to you.')
        else:
            messages.error(request, 'Unable to pick this ticket.')
        
        return redirect('workflow:ticket_detail', reference=reference)


class ResolveTicketView(AgentRequiredMixin, BaseView):
    """Resolve a ticket."""
    
    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        
        if ticket.assigned_to != self.agent:
            messages.error(request, 'This ticket is not assigned to you.')
            return redirect('workflow:ticket_detail', reference=reference)
        
        resolution_notes = request.POST.get('resolution_notes', '')
        ticket_service = self.get_service(TicketService)
        ticket_service.resolve_ticket(ticket, resolution_notes)
        
        # Record performance
        perf_service = self.get_service(PerformanceService)
        perf_service.record_ticket_resolution(self.agent, ticket)
        
        messages.success(request, f'Ticket {ticket.reference} resolved.')
        return redirect('workflow:agent_dashboard')


class EscalateTicketView(AgentRequiredMixin, BaseView):
    """Escalate a ticket to higher level."""
    
    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        reason = request.POST.get('escalation_reason', 'Escalated by agent')
        
        assignment_service = self.get_service(AssignmentService)
        if assignment_service.escalate_ticket(ticket, reason):
            messages.success(request, f'Ticket {ticket.reference} escalated.')
        else:
            messages.error(request, 'Unable to escalate ticket.')
        
        return redirect('workflow:ticket_detail', reference=reference)


class AddNoteView(AgentRequiredMixin, BaseView):
    """Add a note to a ticket."""
    
    def post(self, request, reference):
        ticket = get_object_or_404(Ticket, reference=reference)
        note = request.POST.get('note', '')
        
        if note.strip():
            ticket_service = self.get_service(TicketService)
            ticket_service.add_note(ticket, note)
            messages.success(request, 'Note added.')
        
        return redirect('workflow:ticket_detail', reference=reference)


class TeamDashboardView(AgentRequiredMixin, BaseTemplateView):
    """Team/supervisor dashboard view."""
    template_name = 'workflow/team_dashboard.html'
    page_title = 'Team Dashboard'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Check if agent has permission to view team
        if self.agent.max_level < 4:
            messages.error(request, 'You do not have permission to view team dashboard.')
            return redirect('workflow:agent_dashboard')
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perf_service = self.get_service(PerformanceService)
        
        # Team members
        if self.agent.department:
            team = AgentProfile.objects.filter(department=self.agent.department)
        else:
            team = AgentProfile.objects.all()
        
        context['team_members'] = team.select_related('user', 'primary_workclass')
        
        # Unassigned tickets
        context['unassigned_tickets'] = Ticket.objects.filter(
            status__in=['open', 'escalated'],
            assigned_to__isnull=True
        ).order_by('sla_due_at')[:20]
        
        # Overdue tickets
        context['overdue_tickets'] = Ticket.objects.filter(
            status__in=['assigned', 'in_progress'],
            sla_due_at__lt=timezone.now()
        ).select_related('assigned_to').order_by('sla_due_at')[:20]
        
        # Leaderboard
        context['leaderboard'] = perf_service.get_team_leaderboard(
            department=self.agent.department
        )
        
        # Department stats
        context['total_open'] = Ticket.objects.filter(
            status__in=['open', 'assigned', 'in_progress']
        ).count()
        context['total_resolved_today'] = Ticket.objects.filter(
            status='resolved',
            resolved_at__date=timezone.now().date()
        ).count()
        
        return context
