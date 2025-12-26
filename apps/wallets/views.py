"""
Wallet views for managing user wallet, deposits, and transaction history.
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView
)
from apps.wallets.models import Wallet, WalletTransaction
from apps.payments.models import PaymentMethod, Payment
from apps.payments.services import PaymentService
from apps.wallets.services.wallet_service import WalletService


class WalletDashboardView(BaseTemplateView):
    """Main wallet dashboard showing balance and recent activity."""
    template_name = 'wallets/wallet.html'
    page_title = 'My iFin Wallet'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        wallet_service = self.get_service(WalletService)
        # Get or create wallet
        wallet = wallet_service.get_or_create_wallet()
        context['wallet'] = wallet
        
        # Recent transactions
        context['recent_transactions'] = wallet_service.get_transaction_history(wallet, limit=10)
        
        # Payment methods for deposit
        payment_service = self.get_service(PaymentService)
        context['payment_methods'] = payment_service.get_available_methods(purpose='wallet_deposit')
        
        # Pending deposits
        context['pending_deposits'] = payment_service.get_user_payments(
            status='pending', # Or include others if needed
            limit=5
        ).filter(purpose='wallet_deposit')
        
        # Stats
        context.update(wallet_service.get_wallet_statistics(wallet))
        context['total_deposits'] = wallet.transactions.filter(
            transaction_type__in=['deposit', 'credit']
        ).count()
        context['total_payments'] = wallet.transactions.filter(
            transaction_type__in=['payment', 'debit', 'premium_payment']
        ).count()
        
        return context


class WalletTransactionsView(BaseListView):
    """Full transaction history."""
    template_name = 'wallets/transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20
    page_title = 'Transaction History'
    
    def get_queryset(self):
        wallet_service = self.get_service(WalletService)
        wallet = wallet_service.get_or_create_wallet()
        
        tx_type = self.request.GET.get('type')
        return wallet_service.get_transaction_history(wallet, transaction_type=tx_type)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wallet_service = self.get_service(WalletService)
        context['wallet'] = wallet_service.get_or_create_wallet()
        context['transaction_types'] = WalletTransaction.TRANSACTION_TYPES
        context['selected_type'] = self.request.GET.get('type', '')
        return context


class WalletDepositView(BaseTemplateView):
    """Deposit funds into wallet."""
    template_name = 'wallets/deposit.html'
    page_title = 'Deposit Funds'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wallet_service = self.get_service(WalletService)
        context['wallet'] = wallet_service.get_or_create_wallet()
        payment_service = self.get_service(PaymentService)
        context['payment_methods'] = payment_service.get_available_methods(purpose='wallet_deposit')
        return context
    
    def post(self, request, *args, **kwargs):
        wallet_service = self.get_service(WalletService)
        wallet = wallet_service.get_or_create_wallet()
        
        # Get form data
        amount = request.POST.get('amount')
        method_code = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '')
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid amount.')
            return redirect('wallets:deposit')
        
        # Get payment method
        payment_service = self.get_service(PaymentService)
        payment_method = payment_service.get_method_by_code(method_code)
        
        if not payment_method:
            messages.error(request, 'Invalid payment method.')
            return redirect('wallets:deposit')
        
        # Validate amount
        if amount < float(payment_method.min_amount):
            messages.error(request, f'Minimum deposit is {wallet.currency} {payment_method.min_amount}')
            return redirect('wallets:deposit')
        
        if payment_method.max_amount and amount > float(payment_method.max_amount):
            messages.error(request, f'Maximum deposit is {wallet.currency} {payment_method.max_amount}')
            return redirect('wallets:deposit')
        
        # Build payment details
        payment_details = {}
        if phone_number:
            # Format phone number to 254 format
            phone = phone_number.strip()
            if phone.startswith('0'):
                phone = '254' + phone[1:]
            elif phone.startswith('+'):
                phone = phone[1:]
            payment_details['phone_number'] = phone
        
        # Create payment
        try:
            payment = payment_service.create_payment(
                payment_method=payment_method,
                amount=amount,
                purpose='wallet_deposit',
                purpose_reference=str(wallet.id),
                payment_details=payment_details
            )
            
            # Route based on payment method
            if payment_method.code == 'mpesa':
                # M-Pesa STK Push flow
                messages.info(request, 'Check your phone for the M-Pesa prompt.')
                return redirect('wallets:mpesa_stk', payment_ref=payment.reference)
            elif payment_method.requires_proof:
                # P2P flow (Bank transfer)
                messages.info(request, 'Please complete the transfer and upload proof.')
                return redirect('wallets:deposit_proof', payment_ref=payment.reference)
            else:
                # Other methods
                return redirect('wallets:deposit_process', payment_ref=payment.reference)
                
        except Exception as e:
            messages.error(request, f'Error creating payment: {str(e)}')
            return redirect('wallets:deposit')


class MpesaSTKView(BaseTemplateView):
    """M-Pesa STK Push payment page."""
    template_name = 'wallets/mpesa_stk.html'
    page_title = 'M-Pesa Payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_ref = self.kwargs.get('payment_ref')
        context['payment'] = get_object_or_404(
            Payment, 
            reference=payment_ref, 
            user=self.request.user
        )
        wallet_service = self.get_service(WalletService)
        context['wallet'] = wallet_service.get_or_create_wallet()
        return context
    
    def post(self, request, *args, **kwargs):
        """Initiate STK Push."""
        payment_ref = self.kwargs.get('payment_ref')
        payment = get_object_or_404(Payment, reference=payment_ref, user=request.user)
        
        phone_number = request.POST.get('phone_number', '')
        
        # Format phone number
        phone = phone_number.strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        
        if not phone.startswith('254') or len(phone) != 12:
            messages.error(request, 'Please enter a valid phone number (format: 07XX XXX XXX)')
            return redirect('wallets:mpesa_stk', payment_ref=payment_ref)
        
        # Update payment with phone number
        payment.payment_details['phone_number'] = phone
        payment.status = 'processing'
        payment.save()
        
        # TODO: Integrate with actual M-Pesa STK Push API
        # For now, simulate the STK push was sent
        messages.success(request, f'STK Push sent to {phone}. Enter your M-Pesa PIN to complete.')
        
        return redirect('wallets:mpesa_status', payment_ref=payment_ref)


class MpesaStatusView(BaseTemplateView):
    """Check M-Pesa payment status."""
    template_name = 'wallets/mpesa_status.html'
    page_title = 'Payment Status'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_ref = self.kwargs.get('payment_ref')
        context['payment'] = get_object_or_404(
            Payment, 
            reference=payment_ref, 
            user=self.request.user
        )
        wallet_service = self.get_service(WalletService)
        context['wallet'] = wallet_service.get_or_create_wallet()
        return context


class DepositProofView(BaseTemplateView):
    """Upload proof of payment for P2P deposits (Bank Transfer)."""
    template_name = 'wallets/deposit_proof.html'
    page_title = 'Upload Payment Proof'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_ref = self.kwargs.get('payment_ref')
        context['payment'] = get_object_or_404(
            Payment, 
            reference=payment_ref, 
            user=self.request.user
        )
        wallet_service = self.get_service(WalletService)
        context['wallet'] = wallet_service.get_or_create_wallet()
        
        # Get payment accounts for P2P
        if context['payment'].payment_method:
            context['payment_accounts'] = context['payment'].payment_method.accounts.filter(is_active=True)
        
        return context
    
    def post(self, request, *args, **kwargs):
        payment_ref = self.kwargs.get('payment_ref')
        payment = get_object_or_404(Payment, reference=payment_ref, user=request.user)
        
        # Get form data
        proof_image = request.FILES.get('proof_image')
        transaction_reference = request.POST.get('transaction_reference', '')
        sender_name = request.POST.get('sender_name', '')
        sender_number = request.POST.get('sender_number', '')
        
        if not proof_image:
            messages.error(request, 'Please upload proof of payment.')
            return redirect('wallets:deposit_proof', payment_ref=payment_ref)
        
        try:
            payment_service = self.get_service(PaymentService)
            payment_service.submit_proof(
                payment=payment,
                proof_image=proof_image,
                transaction_reference=transaction_reference,
                sender_name=sender_name,
                sender_number=sender_number
            )
            messages.success(request, 'Proof submitted! We will verify and credit your wallet shortly.')
            return redirect('wallets:wallet')
        except Exception as e:
            messages.error(request, f'Error submitting proof: {str(e)}')
            return redirect('wallets:deposit_proof', payment_ref=payment_ref)


class DepositProcessView(BaseTemplateView):
    """Process non-proof payments."""
    template_name = 'wallets/deposit_process.html'
    page_title = 'Processing Deposit'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_ref = self.kwargs.get('payment_ref')
        context['payment'] = get_object_or_404(
            Payment, 
            reference=payment_ref, 
            user=self.request.user
        )
        return context
