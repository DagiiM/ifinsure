from decimal import Decimal
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone

from apps.core.services.base import BaseService, service_action
from apps.payments.models import Payment, PaymentMethod, PaymentAccount, PaymentProof
from apps.payments.signals import (
    payment_created, 
    payment_initiated, 
    payment_completed,
    proof_submitted
)


class PaymentService(BaseService):
    """
    Service class for payment operations.
    Use this as the main entry point for payment operations from other apps.
    """
    
    model = Payment
    
    def get_available_methods(self, purpose: str = None) -> list:
        """Get all available payment methods."""
        methods = PaymentMethod.objects.filter(is_active=True)
        return list(methods)
    
    def get_method_by_code(self, code: str) -> Optional[PaymentMethod]:
        """Get payment method by code."""
        try:
            return PaymentMethod.objects.get(code=code, is_active=True)
        except PaymentMethod.DoesNotExist:
            return None
    
    @service_action(audit=True)
    def create_payment(
        self,
        payment_method: PaymentMethod,
        amount: Decimal,
        purpose: str,
        purpose_reference: str = '',
        payment_account: PaymentAccount = None,
        payment_details: Dict[str, Any] = None,
        expires_in_hours: int = 24
    ) -> Payment:
        """
        Create a new payment request.
        """
        # Validate amount
        if amount < payment_method.min_amount:
            raise ValueError(f"Amount must be at least {payment_method.min_amount}")
        if payment_method.max_amount and amount > payment_method.max_amount:
            raise ValueError(f"Amount cannot exceed {payment_method.max_amount}")
        
        # Determine initial status
        if payment_method.requires_proof:
            initial_status = 'awaiting_proof'
        else:
            initial_status = 'pending'
        
        payment = self.create(
            user=self._current_user,
            payment_method=payment_method,
            payment_account=payment_account,
            amount=amount,
            purpose=purpose,
            purpose_reference=purpose_reference,
            status=initial_status,
            payment_details=payment_details or {},
            expires_at=timezone.now() + timezone.timedelta(hours=expires_in_hours)
        )
        
        # Send signal
        payment_created.send(sender=self.__class__, payment=payment)
        
        return payment
    
    @service_action(audit=True)
    def submit_proof(
        self,
        payment: Payment,
        proof_image,
        transaction_reference: str = '',
        sender_name: str = '',
        sender_number: str = '',
        amount_paid: Decimal = None,
        payment_date=None,
        additional_notes: str = ''
    ) -> PaymentProof:
        """
        Submit proof of payment for P2P transactions.
        """
        if not payment.requires_proof:
            raise ValueError("This payment method doesn't require proof")
        
        proof = PaymentProof.objects.create(
            payment=payment,
            proof_image=proof_image,
            transaction_reference=transaction_reference,
            sender_name=sender_name,
            sender_number=sender_number,
            amount_paid=amount_paid,
            payment_date=payment_date,
            additional_notes=additional_notes
        )
        
        # Update payment status
        self.update(payment, status='proof_submitted')
        
        # Send signal
        proof_submitted.send(sender=self.__class__, proof=proof)
        
        return proof
    
    @service_action(audit=True)
    def verify_proof(
        self,
        proof: PaymentProof,
        approved: bool,
        rejection_reason: str = ''
    ) -> PaymentProof:
        """
        Verify a submitted payment proof.
        """
        if approved:
            proof.approve(self._current_user)
        else:
            proof.reject(self._current_user, rejection_reason)
        
        return proof
    
    @service_action(audit=True)
    def complete_payment(self, payment: Payment, provider_reference: str = '') -> Payment:
        """
        Mark a payment as completed.
        """
        update_data = {
            'status': 'completed',
            'completed_at': timezone.now()
        }
        if provider_reference:
            update_data['provider_reference'] = provider_reference
            
        payment = self.update(payment, **update_data)
        
        # Send signal
        payment_completed.send(sender=self.__class__, payment=payment)
        
        return payment
    
    def get_user_payments(self, user=None, status: str = None, limit: int = None):
        """Get payments for a user."""
        target_user = user or self._current_user
        payments = self.model.objects.filter(user=target_user)
        if status:
            payments = payments.filter(status=status)
        if limit:
            payments = payments[:limit]
        return payments
    
    def get_payment_by_reference(self, reference: str) -> Optional[Payment]:
        """Get payment by reference."""
        try:
            return self.model.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return None


class WalletServiceFacade:
    """
    Facade for wallet operations from other apps.
    Now correctly uses WalletService.
    """
    
    def __init__(self, user=None):
        from apps.wallets.services.wallet_service import WalletService
        self.service = WalletService(user=user)
    
    def get_or_create_wallet(self, user=None):
        """Get or create wallet for user."""
        return self.service.get_or_create_wallet(user=user)
    
    def get_balance(self, user=None) -> Decimal:
        """Get user's wallet balance."""
        wallet = self.get_or_create_wallet(user=user)
        return wallet.balance
    
    def credit(self, user, amount: Decimal, description: str = '', reference: str = None) -> bool:
        """Credit user's wallet."""
        wallet = self.get_or_create_wallet(user=user)
        self.service.deposit(wallet, amount, description, reference or '')
        return True
    
    def debit(self, user, amount: Decimal, description: str = '', reference: str = None) -> bool:
        """Debit user's wallet (returns False if insufficient funds)."""
        wallet = self.get_or_create_wallet(user=user)
        if wallet.balance < amount:
            return False
        self.service.withdraw(wallet, amount, description, reference or '')
        return True
    
    def can_pay(self, user, amount: Decimal) -> bool:
        """Check if user has sufficient balance."""
        wallet = self.get_or_create_wallet(user=user)
        return wallet.balance >= amount
    
    def get_transactions(self, user, limit: int = None):
        """Get wallet transactions for user."""
        wallet = self.get_or_create_wallet(user=user)
        return self.service.get_transaction_history(wallet, limit=limit)
