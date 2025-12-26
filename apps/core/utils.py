"""
Core utility functions.
"""
from django.utils import timezone
import hashlib
import secrets


def generate_reference(prefix: str, length: int = 8) -> str:
    """
    Generate a unique reference number.
    
    Args:
        prefix: Prefix for the reference (e.g., 'POL', 'CLM')
        length: Length of the random part
    
    Returns:
        Reference string like 'POL-20241223-AB12CD34'
    """
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(length // 2).upper()
    return f"{prefix}-{date_part}-{random_part}"


def get_client_ip(request) -> str:
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def truncate_string(s: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate string to max_length with suffix."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def format_currency(amount, currency: str = 'KES') -> str:
    """Format amount as currency string."""
    return f"{currency} {amount:,.2f}"


def calculate_age(birth_date) -> int:
    """Calculate age from birth date."""
    if not birth_date:
        return 0
    today = timezone.now().date()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def mask_email(email: str) -> str:
    """Mask email for privacy - show first 2 chars and domain."""
    if not email or '@' not in email:
        return email
    local, domain = email.rsplit('@', 1)
    if len(local) <= 2:
        masked = local
    else:
        masked = local[:2] + '*' * (len(local) - 2)
    return f"{masked}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number for privacy - show last 4 digits."""
    if not phone or len(phone) < 4:
        return phone
    return '*' * (len(phone) - 4) + phone[-4:]
