from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from apps.core.services.base import BaseService, service_action
from apps.policies.models import Policy, PolicyApplication


class PolicyService(BaseService):
    """Business logic for policy operations."""
    
    model = Policy
    
    def calculate_premium(self, application: PolicyApplication) -> Decimal:
        """
        Calculate premium based on product and coverage.
        """
        product = application.product
        premium = product.calculate_premium(application.requested_coverage)
        
        # Adjust for payment frequency
        frequency_multipliers = {
            'monthly': Decimal('1.05'),  # 5% premium for monthly
            'quarterly': Decimal('1.03'),
            'semi_annual': Decimal('1.01'),
            'annual': Decimal('1.00'),
        }
        multiplier = frequency_multipliers.get(application.payment_frequency, Decimal('1.00'))
        
        return (premium * multiplier).quantize(Decimal('0.01'))
    
    @service_action(audit=True)
    def submit_application(self, application: PolicyApplication) -> PolicyApplication:
        """
        Submit a draft application for review.
        """
        if application.status != 'draft':
            raise ValueError('Only draft applications can be submitted')
        
        # Calculate premium first (needed for payment calculation)
        application.calculated_premium = self.calculate_premium(application)
        
        # Set up payment requirements based on product configuration
        from apps.policies.services import ApplicationPaymentService
        payment_service = ApplicationPaymentService(user=self._current_user)
        payment_service.setup_application_payment(application)
        
        # Check if payment is required and complete
        can_submit, reason = payment_service.can_submit_application(application)
        if not can_submit:
            raise ValueError(f'Cannot submit application: {reason}')
        
        # Now submit
        application.status = 'submitted'
        application.submitted_at = timezone.now()
        application.save()
        
        # Log action
        self._log_action('update', instance=application, changes={
            'status': 'submitted', 
            'premium': str(application.calculated_premium),
            'payment_status': application.payment_status
        })
        
        return application
    
    @service_action(audit=True)
    def approve_application(
        self,
        application: PolicyApplication,
        notes: str = ''
    ) -> Policy:
        """
        Approve application and create policy.
        """
        reviewer = self._current_user
        
        if application.status not in ['submitted', 'under_review']:
            raise ValueError('Application must be submitted or under review to approve')
        
        # SECURITY: Prevent self-approval - applicant cannot approve their own application
        if application.applicant == reviewer:
            raise PermissionError('You cannot approve your own application')
        
        # SECURITY: Only staff or agents can approve applications
        if not (reviewer.is_staff or getattr(reviewer, 'user_type', '') == 'agent'):
            raise PermissionError('Only staff or agents can approve applications')
        
        # Calculate dates
        start_date = timezone.now().date()
        end_date = start_date + relativedelta(months=application.requested_term_months)
        
        # Create policy
        policy = self.create(
            customer=application.applicant,
            product=application.product,
            agent=application.assigned_agent,
            status='active',
            premium_amount=application.calculated_premium,
            coverage_amount=application.requested_coverage,
            payment_frequency=application.payment_frequency,
            start_date=start_date,
            end_date=end_date,
            beneficiary_name=application.beneficiary_name,
            beneficiary_relationship=application.beneficiary_relationship,
            beneficiary_phone=application.beneficiary_phone,
            notes=notes,
        )
        
        # Update application
        application.status = 'approved'
        application.reviewed_at = timezone.now()
        application.reviewed_by = reviewer
        application.policy = policy
        application.notes = notes
        application.save()
        
        # Log action
        self._log_action('approve', instance=application, changes={'policy_number': policy.policy_number})
        
        return policy
    
    @service_action(audit=True)
    def reject_application(
        self,
        application: PolicyApplication,
        reason: str
    ) -> PolicyApplication:
        """
        Reject an application.
        """
        reviewer = self._current_user
        
        if application.status not in ['submitted', 'under_review']:
            raise ValueError('Application must be submitted or under review to reject')
        
        # SECURITY: Prevent self-rejection
        if application.applicant == reviewer:
            raise PermissionError('You cannot reject your own application')
        
        # SECURITY: Only staff or agents can reject applications
        if not (reviewer.is_staff or getattr(reviewer, 'user_type', '') == 'agent'):
            raise PermissionError('Only staff or agents can reject applications')
        
        if not reason.strip():
            raise ValueError('Rejection reason is required')
        
        application.status = 'rejected'
        application.reviewed_at = timezone.now()
        application.reviewed_by = reviewer
        application.rejection_reason = reason
        application.save()
        
        # Log action
        self._log_action('reject', instance=application, changes={'reason': reason})
        
        return application
    
    @service_action(audit=True)
    def cancel_policy(self, policy: Policy, reason: str = '') -> Policy:
        """
        Cancel an active policy.
        """
        if policy.status not in ['active', 'pending', 'suspended']:
            raise ValueError('Only active, pending, or suspended policies can be cancelled')
        
        updated_policy = self.update(policy, status='cancelled', notes=f"Cancelled: {reason}" if reason else policy.notes)
        
        self._log_action('update', instance=updated_policy, changes={'status': 'cancelled', 'reason': reason})
        
        return updated_policy
    
    def get_customer_policies(self, customer, status=None):
        """
        Get policies for a customer.
        """
        qs = self.get_queryset().filter(
            customer=customer,
            is_active=True
        ).select_related('product', 'agent')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_agent_policies(self, agent, status=None):
        """
        Get policies managed by an agent.
        """
        qs = self.get_queryset().filter(
            agent=agent,
            is_active=True
        ).select_related('product', 'customer')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_expiring_policies(self, days: int = 30):
        """
        Get policies expiring within specified days.
        """
        today = timezone.now().date()
        end_date = today + timezone.timedelta(days=days)
        
        return self.get_queryset().filter(
            status='active',
            end_date__gte=today,
            end_date__lte=end_date,
            is_active=True
        ).select_related('customer', 'product')
