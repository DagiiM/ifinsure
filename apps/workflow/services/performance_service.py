from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from apps.core.services.base import BaseService, service_action
from apps.workflow.models import Ticket, AgentProfile, AgentPerformance, Department


class PerformanceService(BaseService):
    """
    Service for tracking and calculating agent performance.
    """
    
    model = AgentPerformance
    
    def get_or_create_daily_performance(self, agent: AgentProfile, date=None) -> AgentPerformance:
        """
        Get or create daily performance record for an agent.
        """
        if date is None:
            date = timezone.now().date()
        
        performance, created = self.model.objects.get_or_create(
            agent=agent,
            period_type='daily',
            period_start=date,
            defaults={'period_end': date}
        )
        return performance
    
    @service_action(audit=True)
    def record_ticket_resolution(self, agent: AgentProfile, ticket: Ticket):
        """
        Record a ticket resolution in performance metrics.
        """
        performance = self.get_or_create_daily_performance(agent)
        performance.tickets_resolved += 1
        
        # Calculate resolution time
        if ticket.assigned_at:
            resolution_time = (timezone.now() - ticket.assigned_at).total_seconds() / 60
            if performance.avg_resolution_time == 0:
                performance.avg_resolution_time = int(resolution_time)
            else:
                # Running average
                n = performance.tickets_resolved
                performance.avg_resolution_time = int(
                    ((performance.avg_resolution_time * (n - 1)) + resolution_time) / n
                )
        
        # SLA tracking
        if ticket.sla_due_at:
            if timezone.now() <= ticket.sla_due_at:
                performance.sla_met += 1
            else:
                performance.sla_breached += 1
        
        performance.save()
    
    @service_action(audit=True)
    def record_policy_sale(self, agent: AgentProfile, premium_amount: Decimal):
        """
        Record a policy sale in performance metrics.
        """
        performance = self.get_or_create_daily_performance(agent)
        performance.policies_sold += 1
        performance.total_premium_value += premium_amount
        performance.leads_converted += 1
        performance.save()
    
    @service_action(audit=True)
    def record_claim_decision(self, agent: AgentProfile, approved: bool, amount: Decimal):
        """
        Record a claim decision in performance metrics.
        """
        performance = self.get_or_create_daily_performance(agent)
        if approved:
            performance.claims_approved += 1
        else:
            performance.claims_rejected += 1
        performance.total_claims_value += amount
        performance.save()
    
    def get_agent_stats(self, agent: AgentProfile, days: int = 30) -> dict:
        """
        Get aggregated stats for an agent over a period.
        """
        from django.db.models import Sum, Avg
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        records = self.get_queryset().filter(
            agent=agent,
            period_start__gte=start_date
        )
        
        stats = records.aggregate(
            total_assigned=Sum('tickets_assigned'),
            total_resolved=Sum('tickets_resolved'),
            total_escalated=Sum('tickets_escalated'),
            avg_resolution=Avg('avg_resolution_time'),
            sla_met=Sum('sla_met'),
            sla_breached=Sum('sla_breached'),
            policies=Sum('policies_sold'),
            premium=Sum('total_premium_value'),
            claims_approved=Sum('claims_approved'),
            claims_rejected=Sum('claims_rejected'),
        )
        
        # Calculate rates
        total_sla = (stats['sla_met'] or 0) + (stats['sla_breached'] or 0)
        stats['sla_compliance'] = round(
            ((stats['sla_met'] or 0) / total_sla * 100) if total_sla > 0 else 100, 1
        )
        
        total_assigned = stats['total_assigned'] or 0
        total_resolved = stats['total_resolved'] or 0
        stats['resolution_rate'] = round(
            (total_resolved / total_assigned * 100) if total_assigned > 0 else 0, 1
        )
        
        return stats
    
    def get_team_leaderboard(self, department: Department = None, limit: int = 10) -> list:
        """
        Get top performing agents.
        """
        from django.db.models import Sum
        
        start_date = timezone.now().date() - timedelta(days=30)
        
        queryset = self.get_queryset().filter(
            period_start__gte=start_date
        )
        
        if department:
            queryset = queryset.filter(agent__department=department)
        
        leaderboard = queryset.values(
            'agent__id', 
            'agent__user__first_name',
            'agent__user__last_name',
            'agent__user__email'
        ).annotate(
            total_resolved=Sum('tickets_resolved'),
            total_premium=Sum('total_premium_value'),
            total_policies=Sum('policies_sold')
        ).order_by('-total_resolved')[:limit]
        
        return list(leaderboard)
