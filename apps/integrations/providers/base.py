"""
Base classes and interfaces for integration providers.
All provider implementations should inherit from these base classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from decimal import Decimal
import time


@dataclass
class PaymentRequest:
    """Standard payment request structure"""
    amount: Decimal
    currency: str = 'KES'
    phone_number: Optional[str] = None
    email: Optional[str] = None
    description: str = ''
    reference: str = ''
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'amount': str(self.amount),
            'currency': self.currency,
            'phone_number': self.phone_number,
            'email': self.email,
            'description': self.description,
            'reference': self.reference,
            'callback_url': self.callback_url,
            'metadata': self.metadata
        }


@dataclass
class PaymentResult:
    """Standard payment result structure"""
    success: bool
    transaction_id: Optional[str] = None
    provider_reference: Optional[str] = None
    status: str = 'pending'
    message: str = ''
    raw_response: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'transaction_id': self.transaction_id,
            'provider_reference': self.provider_reference,
            'status': self.status,
            'message': self.message
        }


@dataclass
class SMSRequest:
    """Standard SMS request structure"""
    to: str  # Phone number
    message: str
    sender_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SMSResult:
    """Standard SMS result structure"""
    success: bool
    message_id: Optional[str] = None
    status: str = 'pending'
    message: str = ''
    cost: Optional[Decimal] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for all providers"""
    
    def __init__(self, config: 'IntegrationConfig'):
        self.config = config
        self.credentials = config.credentials
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test provider connectivity"""
        pass
    
    def get_credential(self, key: str, default=None):
        """Safely get a credential value"""
        return self.credentials.get(key, default)
    
    def log_request(self, action: str, request_data: Dict, response_data: Dict,
                    status: str, error_message: str = '', response_time_ms: int = None,
                    reference_type: str = '', reference_id: str = ''):
        """Log an API request"""
        from apps.integrations.models import IntegrationLog
        return IntegrationLog.log_request(
            config=self.config,
            action=action,
            request_data=request_data,
            response_data=response_data,
            status=status,
            error_message=error_message,
            response_time_ms=response_time_ms,
            reference_type=reference_type,
            reference_id=reference_id
        )
    
    def _timed_request(self, func, *args, **kwargs):
        """Execute a function and return result with timing"""
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_ms = int((time.time() - start_time) * 1000)
        return result, elapsed_ms


class BasePaymentProvider(BaseProvider):
    """Abstract base class for payment providers"""
    
    @property
    @abstractmethod
    def supported_currencies(self) -> List[str]:
        """Return list of supported currency codes"""
        pass
    
    @abstractmethod
    def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Initiate a payment request"""
        pass
    
    @abstractmethod
    def verify_payment(self, transaction_id: str) -> PaymentResult:
        """Verify payment status"""
        pass
    
    @abstractmethod
    def process_webhook(self, payload: Dict[str, Any]) -> PaymentResult:
        """Process incoming webhook"""
        pass
    
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Initiate refund (optional - not all providers support this)"""
        return PaymentResult(
            success=False,
            message='Refunds not supported by this provider'
        )
    
    def supports_currency(self, currency: str) -> bool:
        """Check if currency is supported"""
        return currency.upper() in self.supported_currencies


class BaseSMSProvider(BaseProvider):
    """Abstract base class for SMS providers"""
    
    @abstractmethod
    def send_sms(self, request: SMSRequest) -> SMSResult:
        """Send an SMS message"""
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        pass
    
    def send_bulk_sms(self, requests: List[SMSRequest]) -> List[SMSResult]:
        """Send bulk SMS (default implementation sends one by one)"""
        return [self.send_sms(req) for req in requests]


class BaseEmailProvider(BaseProvider):
    """Abstract base class for email providers"""
    
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, 
                   html_body: Optional[str] = None,
                   from_email: Optional[str] = None) -> Dict[str, Any]:
        """Send an email"""
        pass
    
    @abstractmethod
    def send_template_email(self, to: str, template_id: str, 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email using a template"""
        pass


class BaseStorageProvider(BaseProvider):
    """Abstract base class for storage providers"""
    
    @abstractmethod
    def upload_file(self, file_path: str, destination: str) -> Dict[str, Any]:
        """Upload a file"""
        pass
    
    @abstractmethod
    def download_file(self, source: str, destination: str) -> bool:
        """Download a file"""
        pass
    
    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for a file"""
        pass
