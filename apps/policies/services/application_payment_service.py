from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.core.services.base import BaseService, service_action
from apps.policies.models import PolicyApplication


class ApplicationPaymentService(BaseService):
    """
    Service to manage payments for policy applications.
    Integrates with CRM product payment configuration.
    
    Supports three payment modes configured per product:
    - 'none': No payment required at application
    - 'convenience_only': Only convenience/processing fee required
    - 'full': Convenience fee + full premium required
    """
    
    model = PolicyApplication
    
    def calculate_application_payment(self, application):
        """
        Calculate what payment is required for an application based on product config.
        """
        # Try to get CRM product for payment configuration
        crm_product = self._get_crm_product(application)
        
        if not crm_product:
            # Default: convenience fee only of KES 500
            return {
                'required': True,
                'total_amount': Decimal('500.00'),
                'convenience_fee': Decimal('500.00'),
                'premium_amount': Decimal('0.00'),
                'payment_mode': 'convenience_only',
                'breakdown': 'Application fee: KES 500.00'
            }
        
        # Get calculated premium from application
        premium = application.calculated_premium or Decimal('0.00')
        
        # Calculate based on product configuration
        total, breakdown = crm_product.get_application_payment_amount(premium)
        
        if crm_product.application_payment_mode == 'none':
            return {
                'required': False,
                'total_amount': Decimal('0.00'),
                'convenience_fee': Decimal('0.00'),
                'premium_amount': Decimal('0.00'),
                'payment_mode': 'none',
                'breakdown': 'No payment required at application'
            }
        
        if crm_product.application_payment_mode == 'convenience_only':
            desc = f"Application fee: KES {breakdown['convenience_fee']:,.2f}"
        else:
            desc = f"Application fee: KES {breakdown['convenience_fee']:,.2f} + Premium: KES {breakdown['premium']:,.2f}"
        
        return {
            'required': True,
            'total_amount': total,
            'convenience_fee': breakdown['convenience_fee'],
            'premium_amount': breakdown['premium'],
            'payment_mode': crm_product.application_payment_mode,
            'breakdown': desc
        }
    
    def _get_crm_product(self, application):
        """Try to find matching CRM InsuranceProduct for an application."""
        try:
            from apps.crm.models import InsuranceProduct as CRMProduct
            
            # Try matching by product code
            product = application.product
            if hasattr(product, 'code') and product.code:
                crm_product = CRMProduct.objects.filter(
                    code=product.code,
                    is_active=True
                ).first()
                if crm_product:
                    return crm_product
            
            # Try matching by name (fallback)
            if hasattr(product, 'name') and product.name:
                crm_product = CRMProduct.objects.filter(
                    name__icontains=product.name,
                    is_active=True
                ).first()
                if crm_product:
                    return crm_product
                    
        except Exception:
            pass
        
        return None
    
    @service_action(audit=True)
    def setup_application_payment(self, application):
        """
        Set up payment requirements for an application before submission.
        Updates the application with payment amounts.
        """
        payment_info = self.calculate_application_payment(application)
        
        application.convenience_fee_amount = payment_info['convenience_fee']
        application.premium_amount = payment_info['premium_amount']
        application.total_payment_due = payment_info['total_amount']
        
        if not payment_info['required']:
            application.payment_status = 'not_required'
        else:
            application.payment_status = 'pending'
        
        application.save(update_fields=[
            'convenience_fee_amount',
            'premium_amount', 
            'total_payment_due',
            'payment_status'
        ])
        
        return application
    
    @service_action(audit=True)
    def record_payment(self, application, amount, reference=None):
        """
        Record a payment against an application.
        """
        application.amount_paid += Decimal(str(amount))
        
        if reference:
            application.payment_reference = reference
        
        # Update payment status
        if application.amount_paid >= application.total_payment_due:
            application.payment_status = 'paid'
            application.paid_at = timezone.now()
        elif application.amount_paid > Decimal('0.00'):
            application.payment_status = 'partial'
        
        application.save(update_fields=[
            'amount_paid',
            'payment_reference',
            'payment_status',
            'paid_at'
        ])
        
        self._log_action('payment_recorded', instance=application, details={'amount': str(amount), 'reference': reference})
        
        # Return status message
        if application.payment_status == 'paid':
            return True, "Payment received. Application ready for submission."
        elif application.payment_status == 'partial':
            remaining = application.total_payment_due - application.amount_paid
            return True, f"Partial payment received. KES {remaining:,.2f} remaining."
        
        return True, "Payment recorded successfully."
    
    def can_submit_application(self, application):
        """
        Check if an application can be submitted based on payment status.
        """
        if application.payment_status == 'not_required':
            return True, "No payment required"
        
        if application.payment_status == 'paid':
            return True, "Payment complete"
        
        if application.payment_status == 'pending':
            return False, f"Payment of KES {application.total_payment_due:,.2f} required"
        
        if application.payment_status == 'partial':
            remaining = application.total_payment_due - application.amount_paid
            return False, f"Remaining payment of KES {remaining:,.2f} required"
        
        return False, "Payment status unknown"
    
    def get_payment_summary(self, application):
        """Get a summary of payment status for an application."""
        return {
            'convenience_fee': application.convenience_fee_amount,
            'premium_amount': application.premium_amount,
            'total_due': application.total_payment_due,
            'amount_paid': application.amount_paid,
            'balance': application.total_payment_due - application.amount_paid,
            'status': application.payment_status,
            'status_display': application.get_payment_status_display(),
            'is_paid': application.payment_status == 'paid',
            'reference': application.payment_reference,
            'paid_at': application.paid_at,
        }
