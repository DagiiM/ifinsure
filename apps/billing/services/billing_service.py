from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from apps.core.services.base import BaseService, service_action
from apps.billing.models import Invoice, Payment


class BillingService(BaseService):
    """Business logic for billing operations."""
    
    model = Invoice
    
    @service_action(audit=True)
    def create_invoice(
        self,
        customer,
        amount: Decimal,
        due_date,
        policy=None,
        description: str = ''
    ) -> Invoice:
        """
        Create a new invoice.
        """
        invoice = self.create(
            customer=customer,
            policy=policy,
            amount=amount,
            due_date=due_date,
            description=description,
            status='pending'
        )
        
        return invoice
    
    @service_action(audit=True)
    def record_payment(
        self,
        invoice: Invoice,
        amount: Decimal,
        payment_method: str,
        transaction_id: str = '',
        notes: str = ''
    ) -> Payment:
        """
        Record a payment against an invoice.
        """
        if amount <= 0:
            raise ValueError('Payment amount must be positive')
        
        if amount > invoice.balance:
            raise ValueError(f'Payment amount exceeds balance ({invoice.balance})')
        
        # Payment is not this service's primary model, but we can still create it
        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            status='completed',
            received_by=self._current_user,
            transaction_id=transaction_id,
            notes=notes
        )
        
        # Update invoice
        invoice.paid_amount += amount
        invoice.update_status()
        
        self._log_action('create', instance=payment, details={
            'invoice': invoice.invoice_number,
            'amount': str(amount),
            'method': payment_method
        })
        
        return payment
    
    @service_action(audit=True)
    def cancel_invoice(self, invoice: Invoice, reason: str = '') -> Invoice:
        """
        Cancel an invoice.
        """
        if invoice.status == 'paid':
            raise ValueError('Cannot cancel a paid invoice')
        
        if invoice.paid_amount > 0:
            raise ValueError('Cannot cancel invoice with payments - refund first')
        
        updated_invoice = self.update(invoice, status='cancelled', notes=f"Cancelled: {reason}" if reason else invoice.notes)
        
        self._log_action('update', instance=updated_invoice, changes={'status': 'cancelled', 'reason': reason})
        
        return updated_invoice
    
    @service_action(audit=True)
    def refund_payment(self, payment: Payment, reason: str = '') -> Payment:
        """
        Refund a payment.
        """
        if payment.status != 'completed':
            raise ValueError('Only completed payments can be refunded')
        
        # Update payment
        payment.status = 'refunded'
        payment.notes = f"{payment.notes}\nRefunded: {reason}".strip()
        payment.save()
        
        # Update invoice
        invoice = payment.invoice
        invoice.paid_amount -= payment.amount
        invoice.update_status()
        
        self._log_action('update', instance=payment, changes={'status': 'refunded', 'reason': reason})
        
        return payment
    
    def get_customer_invoices(self, customer, status=None):
        """Get invoices for a customer."""
        qs = self.get_queryset().filter(
            customer=customer,
            is_active=True
        ).select_related('policy')
        
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_overdue_invoices(self):
        """Get all overdue invoices."""
        today = timezone.now().date()
        return self.get_queryset().filter(
            due_date__lt=today,
            status__in=['pending', 'partial'],
            is_active=True
        ).select_related('customer', 'policy')
    
    def get_billing_statistics(self):
        """Get billing statistics for dashboard."""
        from django.db.models import Sum, Count
        
        qs = self.get_queryset().filter(is_active=True)
        
        return {
            'total_invoiced': qs.aggregate(total=Sum('amount'))['total'] or 0,
            'total_collected': qs.aggregate(total=Sum('paid_amount'))['total'] or 0,
            'pending_count': qs.filter(status='pending').count(),
            'overdue_count': qs.filter(status='overdue').count(),
            'pending_amount': qs.filter(
                status__in=['pending', 'partial', 'overdue']
            ).aggregate(total=Sum('amount') - Sum('paid_amount'))['total'] or 0,
        }
    
    @service_action(audit=True)
    def generate_policy_invoice(self, policy) -> Invoice:
        """
        Generate invoice for policy premium.
        """
        # Calculate due date based on payment frequency
        frequency_days = {
            'monthly': 30,
            'quarterly': 90,
            'semi_annual': 180,
            'annual': 365,
        }
        days = frequency_days.get(policy.payment_frequency, 30)
        due_date = timezone.now().date() + timezone.timedelta(days=14)  # 14 days to pay
        
        return self.create_invoice(
            customer=policy.customer,
            amount=policy.premium_amount,
            due_date=due_date,
            policy=policy,
            description=f"Premium payment for {policy.policy_number}"
        )
