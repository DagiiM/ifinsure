from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from apps.core.services.base import BaseService, service_action
from apps.claims.models import Claim, ClaimStatusHistory


class ClaimService(BaseService):
    """Business logic for claim operations."""
    
    model = Claim
    
    def _log_status_change(self, claim, old_status, new_status, notes=''):
        """Log claim status change."""
        ClaimStatusHistory.objects.create(
            claim=claim,
            old_status=old_status,
            new_status=new_status,
            changed_by=self._current_user,
            notes=notes
        )
    
    @service_action(audit=True)
    def create_claim(
        self,
        claimant,
        policy,
        incident_date,
        incident_description: str,
        claimed_amount,
        claim_type: str = 'general',
        incident_location: str = '',
        **extra_fields
    ):
        """
        Create a new draft claim.
        """
        # Validation
        if not policy:
            raise ValueError('Policy is required')
        
        if policy.status != 'active':
            raise ValueError('Cannot create claim - policy is not active')
        
        if policy.customer != claimant:
            raise ValueError('You can only claim against your own policies')
        
        if claimed_amount is None or Decimal(str(claimed_amount)) <= 0:
            raise ValueError('Claimed amount must be positive')
        
        claim = self.create(
            claimant=claimant,
            policy=policy,
            incident_date=incident_date,
            incident_description=incident_description,
            claimed_amount=Decimal(str(claimed_amount)),
            claim_type=claim_type,
            incident_location=incident_location,
            status='draft',
            **extra_fields
        )
        
        return claim

    @service_action(audit=True)
    def submit_claim(self, claim: Claim) -> Claim:
        """
        Submit a draft claim for review.
        """
        if claim.status != 'draft':
            raise ValueError('Only draft claims can be submitted')
        
        # Validate policy is active
        if claim.policy.status != 'active':
            raise ValueError('Cannot submit claim - policy is not active')
        
        old_status = claim.status
        updated_claim = self.update(claim, status='submitted', submitted_at=timezone.now())
        
        # Log status change
        self._log_status_change(updated_claim, old_status, 'submitted')
        
        return updated_claim
    
    @service_action(audit=True)
    def assign_adjuster(self, claim: Claim, adjuster) -> Claim:
        """
        Assign an adjuster to a claim.
        """
        old_status = claim.status
        update_data = {'assigned_adjuster': adjuster}
        
        if claim.status == 'submitted':
            update_data['status'] = 'under_review'
            self._log_status_change(claim, old_status, 'under_review')
        
        updated_claim = self.update(claim, **update_data)
        
        self._log_action('update', instance=updated_claim, details={'assigned_adjuster': adjuster.email})
        
        return updated_claim
    
    @service_action(audit=True)
    def approve_claim(
        self,
        claim: Claim,
        approved_amount: Decimal,
        notes: str = ''
    ) -> Claim:
        """
        Approve a claim.
        """
        if claim.status not in ['submitted', 'under_review', 'investigating']:
            raise ValueError('Claim cannot be approved in current status')
        
        if approved_amount <= 0:
            raise ValueError('Approved amount must be positive')
        
        if approved_amount > claim.claimed_amount:
            raise ValueError('Approved amount cannot exceed claimed amount')
        
        old_status = claim.status
        
        # Determine status based on approved vs claimed amount
        new_status = 'approved' if approved_amount == claim.claimed_amount else 'partially_approved'
        
        updated_claim = self.update(
            claim,
            status=new_status,
            approved_amount=approved_amount,
            reviewed_at=timezone.now(),
            reviewed_by=self._current_user,
            adjuster_notes=notes if notes else claim.adjuster_notes
        )
        
        self._log_status_change(
            updated_claim, old_status, new_status,
            f'Approved amount: {approved_amount}'
        )
        
        return updated_claim
    
    @service_action(audit=True)
    def reject_claim(self, claim: Claim, reason: str) -> Claim:
        """
        Reject a claim.
        """
        if claim.status not in ['submitted', 'under_review', 'investigating']:
            raise ValueError('Claim cannot be rejected in current status')
        
        if not reason:
            raise ValueError('Rejection reason is required')
        
        old_status = claim.status
        updated_claim = self.update(
            claim,
            status='rejected',
            reviewed_at=timezone.now(),
            reviewed_by=self._current_user,
            rejection_reason=reason
        )
        
        self._log_status_change(updated_claim, old_status, 'rejected', reason)
        
        return updated_claim
    
    @service_action(audit=True)
    def mark_paid(self, claim: Claim, paid_amount: Decimal) -> Claim:
        """
        Mark claim as paid.
        """
        if claim.status not in ['approved', 'partially_approved']:
            raise ValueError('Only approved claims can be marked as paid')
        
        old_status = claim.status
        updated_claim = self.update(claim, status='paid', paid_amount=paid_amount)
        
        self._log_status_change(
            updated_claim, old_status, 'paid',
            f'Payment recorded: {paid_amount}'
        )
        
        return updated_claim
    
    @service_action(audit=True)
    def close_claim(self, claim: Claim, notes: str = '') -> Claim:
        """
        Close a claim.
        """
        if claim.status not in ['paid', 'rejected']:
            raise ValueError('Only paid or rejected claims can be closed')
        
        old_status = claim.status
        adjuster_notes = claim.adjuster_notes
        if notes:
            adjuster_notes = f"{adjuster_notes}\n\nClosed: {notes}".strip()
            
        updated_claim = self.update(claim, status='closed', adjuster_notes=adjuster_notes)
        
        self._log_status_change(updated_claim, old_status, 'closed', notes)
        
        return updated_claim
    
    def get_customer_claims(self, customer, status=None):
        """Get claims for a customer."""
        qs = self.get_queryset().filter(
            claimant=customer,
            is_active=True
        ).select_related('policy', 'policy__product')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_adjuster_claims(self, adjuster, status=None):
        """Get claims assigned to an adjuster."""
        qs = self.get_queryset().filter(
            assigned_adjuster=adjuster,
            is_active=True
        ).select_related('policy', 'claimant', 'policy__product')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_pending_claims(self):
        """Get all pending claims that need attention."""
        return self.get_queryset().filter(
            status__in=['submitted', 'under_review', 'investigating'],
            is_active=True
        ).select_related('policy', 'claimant', 'assigned_adjuster')
    
    def get_claim_statistics(self):
        """Get claim statistics for dashboard."""
        from django.db.models import Count, Sum, Avg
        
        qs = self.get_queryset().filter(is_active=True)
        
        return {
            'total': qs.count(),
            'pending': qs.filter(status__in=['submitted', 'under_review', 'investigating']).count(),
            'approved': qs.filter(status__in=['approved', 'partially_approved']).count(),
            'paid': qs.filter(status='paid').count(),
            'rejected': qs.filter(status='rejected').count(),
            'total_claimed': qs.aggregate(total=Sum('claimed_amount'))['total'] or 0,
            'total_approved': qs.aggregate(total=Sum('approved_amount'))['total'] or 0,
            'total_paid': qs.aggregate(total=Sum('paid_amount'))['total'] or 0,
        }
