"""
Signals for workflow app.
Auto-creates tickets when claims/policies are submitted.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType


# Signal to create agent profile for staff users
@receiver(post_save, sender='accounts.User')
def create_agent_profile_for_staff(sender, instance, created, **kwargs):
    """Create AgentProfile for staff/agent users."""
    if instance.is_staff or getattr(instance, 'is_agent', False):
        from apps.workflow.models import AgentProfile
        AgentProfile.objects.get_or_create(user=instance)


# Auto-create tickets for claims
@receiver(post_save, sender='claims.Claim')
def create_ticket_for_claim(sender, instance, created, **kwargs):
    """Auto-create a workflow ticket when a claim is submitted."""
    if created:
        from apps.workflow.models import Ticket, Department
        from apps.workflow.services import TicketService
        
        # Get claims department
        claims_dept, _ = Department.objects.get_or_create(
            code='CLAIMS',
            defaults={'name': 'Claims Department'}
        )
        
        # Determine priority based on claim amount
        amount = float(instance.amount) if hasattr(instance, 'amount') else 0
        if amount > 500000:
            priority = 'urgent'
        elif amount > 100000:
            priority = 'high'
        elif amount > 50000:
            priority = 'medium'
        else:
            priority = 'low'
        
        # Create ticket
        service = TicketService(user=instance.claimant if hasattr(instance, 'claimant') else None)
        service.create_ticket(
            ticket_type='claim',
            subject=f"Claim: {getattr(instance, 'claim_number', instance.pk)}",
            description=getattr(instance, 'description', ''),
            priority=priority,
            customer=instance.claimant if hasattr(instance, 'claimant') else None,
            linked_object=instance,
            estimated_amount=amount,
            required_department=claims_dept
        )


# Auto-create tickets for policy applications
@receiver(post_save, sender='policies.PolicyApplication')
def create_ticket_for_application(sender, instance, created, **kwargs):
    """Auto-create a workflow ticket when a policy application is submitted."""
    if created:
        from apps.workflow.models import Ticket, Department
        from apps.workflow.services import TicketService
        
        # Get policies department
        policies_dept, _ = Department.objects.get_or_create(
            code='POLICIES',
            defaults={'name': 'Policy Department'}
        )
        
        # Create ticket
        service = TicketService(user=instance.applicant if hasattr(instance, 'applicant') else None)
        service.create_ticket(
            ticket_type='policy',
            subject=f"Policy Application: {getattr(instance, 'application_number', instance.pk)}",
            description=f"New policy application",
            priority='medium',
            customer=instance.applicant if hasattr(instance, 'applicant') else None,
            linked_object=instance,
            estimated_amount=getattr(instance, 'premium_amount', 0),
            required_department=policies_dept
        )
