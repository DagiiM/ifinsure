"""
Signals for payment app - cross-app communication.
"""
from django.dispatch import Signal

# Payment lifecycle signals
payment_created = Signal()  # Provides: payment
payment_initiated = Signal()  # Provides: payment
payment_completed = Signal()  # Provides: payment
payment_failed = Signal()  # Provides: payment, error
payment_refunded = Signal()  # Provides: payment, refund_amount

# Proof signals
proof_submitted = Signal()  # Provides: proof
proof_approved = Signal()  # Provides: proof
proof_rejected = Signal()  # Provides: proof, reason
