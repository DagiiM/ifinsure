"""
Signal handlers for payment events.
Handles cross-app communication when payments are processed.
"""
from django.dispatch import receiver
from apps.payments.signals import payment_completed, payment_failed


@receiver(payment_completed)
def handle_payment_completed(sender, payment, **kwargs):
    """
    Handle successful payment completion.
    Credits the user's wallet if it's a wallet deposit.
    """
    from apps.wallets.models import Wallet
    
    try:
        wallet = Wallet.objects.get(user=payment.user)
        
        # Credit wallet for deposit payments
        if payment.purpose == 'wallet_deposit':
            wallet.credit(
                amount=payment.amount,
                description=f"Deposit via {payment.payment_method.name}",
                reference=payment.reference,
                transaction_type='deposit'
            )
        elif payment.purpose == 'policy_premium':
            # Log premium payment (actual policy update should be handled by policies app)
            wallet.credit(
                amount=payment.amount,
                description=f"Premium payment: {payment.purpose_reference}",
                reference=payment.reference,
                transaction_type='premium_payment'
            )
            # Then immediately debit for the premium
            wallet.debit(
                amount=payment.amount,
                description=f"Premium paid for: {payment.purpose_reference}",
                reference=payment.reference,
                transaction_type='payment'
            )
    except Wallet.DoesNotExist:
        # Log error - this shouldn't happen if signals are set up correctly
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Wallet not found for user {payment.user.id} on payment {payment.reference}")


@receiver(payment_failed)
def handle_payment_failed(sender, payment, error=None, **kwargs):
    """
    Handle failed payment.
    Could send notifications, log errors, etc.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Payment failed: {payment.reference} - {error}")
