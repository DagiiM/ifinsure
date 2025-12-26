from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.core.services.base import BaseService, service_action
from apps.wallets.models import Wallet, WalletTransaction


class WalletService(BaseService):
    """Business logic for wallet operations."""
    
    model = Wallet
    
    @service_action(audit=True)
    def get_or_create_wallet(self, user=None) -> Wallet:
        """
        Get or create wallet for a user.
        """
        target_user = user or self._current_user
        wallet, created = self.model.objects.get_or_create(
            user=target_user,
            defaults={'balance': Decimal('0.00')}
        )
        
        if created:
            self._log_action('create', instance=wallet, details={'event': 'Wallet created'})
        
        return wallet
    
    @service_action(audit=True)
    def deposit(
        self,
        wallet: Wallet,
        amount: Decimal,
        description: str = '',
        reference: str = '',
        payment_method: str = '',
        transaction_id: str = ''
    ) -> WalletTransaction:
        """
        Deposit funds into a wallet.
        """
        if amount <= 0:
            raise ValueError('Deposit amount must be positive')
        
        # Lock the wallet row for update
        wallet = self.model.objects.select_for_update().get(pk=wallet.pk)
        
        # Create transaction
        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance + amount,
            description=description or 'Wallet deposit',
            reference=reference,
            status='completed',
            payment_method=payment_method,
            transaction_id=transaction_id
        )
        
        # Update wallet balance
        wallet.balance += amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        self._log_action('create', instance=txn, changes={'amount': str(amount), 'type': 'deposit'})
        
        return txn
    
    @service_action(audit=True)
    def withdraw(
        self,
        wallet: Wallet,
        amount: Decimal,
        description: str = '',
        reference: str = ''
    ) -> WalletTransaction:
        """
        Withdraw funds from a wallet.
        """
        if amount <= 0:
            raise ValueError('Withdrawal amount must be positive')
        
        # Lock the wallet row for update
        wallet = self.model.objects.select_for_update().get(pk=wallet.pk)
        
        if wallet.balance < amount:
            raise ValueError(f'Insufficient balance. Available: {wallet.balance}')
        
        # Create transaction
        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='withdrawal',
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance - amount,
            description=description or 'Wallet withdrawal',
            reference=reference,
            status='completed'
        )
        
        # Update wallet balance
        wallet.balance -= amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        self._log_action('create', instance=txn, changes={'amount': str(amount), 'type': 'withdrawal'})
        
        return txn
    
    @service_action(audit=True)
    def transfer(
        self,
        from_wallet: Wallet,
        to_wallet: Wallet,
        amount: Decimal,
        description: str = ''
    ):
        """
        Transfer funds between wallets.
        """
        if from_wallet.pk == to_wallet.pk:
            raise ValueError('Cannot transfer to the same wallet')
        
        if amount <= 0:
            raise ValueError('Transfer amount must be positive')
        
        # Lock both wallets (in consistent order to prevent deadlock)
        wallets = self.model.objects.select_for_update().filter(
            pk__in=[from_wallet.pk, to_wallet.pk]
        ).order_by('pk')
        
        wallet_map = {w.pk: w for w in wallets}
        from_wallet = wallet_map[from_wallet.pk]
        to_wallet = wallet_map[to_wallet.pk]
        
        if from_wallet.balance < amount:
            raise ValueError(f'Insufficient balance. Available: {from_wallet.balance}')
        
        # Generate transfer reference
        transfer_ref = f"TRF-{timezone.now():%Y%m%d%H%M%S}-{from_wallet.pk}"
        
        # Create debit transaction
        debit_txn = WalletTransaction.objects.create(
            wallet=from_wallet,
            transaction_type='transfer_out',
            amount=amount,
            balance_before=from_wallet.balance,
            balance_after=from_wallet.balance - amount,
            description=description or f'Transfer to {to_wallet.user}',
            reference=transfer_ref,
            status='completed'
        )
        
        # Create credit transaction
        credit_txn = WalletTransaction.objects.create(
            wallet=to_wallet,
            transaction_type='transfer_in',
            amount=amount,
            balance_before=to_wallet.balance,
            balance_after=to_wallet.balance + amount,
            description=description or f'Transfer from {from_wallet.user}',
            reference=transfer_ref,
            status='completed'
        )
        
        # Update balances
        from_wallet.balance -= amount
        from_wallet.save(update_fields=['balance', 'updated_at'])
        
        to_wallet.balance += amount
        to_wallet.save(update_fields=['balance', 'updated_at'])
        
        self._log_action('create', instance=debit_txn, changes={
            'amount': str(amount),
            'type': 'transfer',
            'from': str(from_wallet.user),
            'to': str(to_wallet.user)
        })
        
        return debit_txn, credit_txn
    
    @service_action(audit=True)
    def pay_invoice(
        self,
        wallet: Wallet,
        invoice,
        amount: Decimal
    ) -> WalletTransaction:
        """
        Pay an invoice from wallet balance.
        """
        if amount <= 0:
            raise ValueError('Payment amount must be positive')
        
        if amount > invoice.balance:
            raise ValueError(f'Amount exceeds invoice balance of {invoice.balance}')
        
        # Lock the wallet
        wallet = self.model.objects.select_for_update().get(pk=wallet.pk)
        
        if wallet.balance < amount:
            raise ValueError(f'Insufficient wallet balance. Available: {wallet.balance}')
        
        # Create transaction
        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='payment',
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance - amount,
            description=f'Payment for invoice {invoice.invoice_number}',
            reference=invoice.invoice_number,
            status='completed'
        )
        
        # Update wallet balance
        wallet.balance -= amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        self._log_action('create', instance=txn, changes={
            'amount': str(amount),
            'type': 'payment',
            'invoice': invoice.invoice_number
        })
        
        return txn
    
    @service_action(audit=True)
    def refund_to_wallet(
        self,
        wallet: Wallet,
        amount: Decimal,
        reason: str = '',
        reference: str = ''
    ) -> WalletTransaction:
        """
        Refund amount to wallet.
        """
        if amount <= 0:
            raise ValueError('Refund amount must be positive')
        
        wallet = self.model.objects.select_for_update().get(pk=wallet.pk)
        
        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='refund',
            amount=amount,
            balance_before=wallet.balance,
            balance_after=wallet.balance + amount,
            description=reason or 'Refund',
            reference=reference,
            status='completed'
        )
        
        wallet.balance += amount
        wallet.save(update_fields=['balance', 'updated_at'])
        
        self._log_action('create', instance=txn, changes={'amount': str(amount), 'type': 'refund', 'reason': reason})
        
        return txn
    
    def get_transaction_history(
        self,
        wallet: Wallet,
        transaction_type: str = None,
        limit: int = None
    ):
        """
        Get transaction history for a wallet.
        """
        qs = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')
        
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        
        if limit:
            qs = qs[:limit]
        
        return qs
    
    def get_wallet_statistics(self, wallet: Wallet) -> dict:
        """Get wallet statistics."""
        from django.db.models import Sum, Count
        
        txns = WalletTransaction.objects.filter(wallet=wallet, status='completed')
        
        deposits = txns.filter(
            transaction_type__in=['deposit', 'transfer_in', 'refund']
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        withdrawals = txns.filter(
            transaction_type__in=['withdrawal', 'payment', 'transfer_out']
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        return {
            'current_balance': wallet.balance,
            'total_deposited': deposits['total'] or Decimal('0'),
            'deposit_count': deposits['count'],
            'total_spent': withdrawals['total'] or Decimal('0'),
            'withdrawal_count': withdrawals['count'],
        }
