"""
M-Pesa Daraja API Integration

This provider implements M-Pesa STK Push (Lipa na M-Pesa Online) for
customer-initiated payments.

Configuration Schema:
{
    "consumer_key": {"type": "password", "required": true, "label": "Consumer Key"},
    "consumer_secret": {"type": "password", "required": true, "label": "Consumer Secret"},
    "shortcode": {"type": "text", "required": true, "label": "Business Shortcode"},
    "passkey": {"type": "password", "required": true, "label": "Passkey"},
    "initiator_name": {"type": "text", "required": false, "label": "Initiator Name"},
    "security_credential": {"type": "password", "required": false, "label": "Security Credential"}
}
"""

import requests
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

from ..base import BasePaymentProvider, PaymentRequest, PaymentResult


class MPesaProvider(BasePaymentProvider):
    """M-Pesa Daraja API Integration"""
    
    SANDBOX_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_URL = "https://api.safaricom.co.ke"
    
    provider_name = "M-Pesa"
    supported_currencies = ["KES"]
    
    # Configuration schema for admin form
    CONFIG_SCHEMA = {
        "consumer_key": {
            "type": "password",
            "required": True,
            "label": "Consumer Key",
            "help_text": "Your M-Pesa API Consumer Key from Daraja portal"
        },
        "consumer_secret": {
            "type": "password",
            "required": True,
            "label": "Consumer Secret",
            "help_text": "Your M-Pesa API Consumer Secret from Daraja portal"
        },
        "shortcode": {
            "type": "text",
            "required": True,
            "label": "Business Shortcode",
            "placeholder": "174379",
            "help_text": "Your Paybill or Till number"
        },
        "passkey": {
            "type": "password",
            "required": True,
            "label": "Passkey",
            "help_text": "The Lipa na M-Pesa passkey"
        }
    }
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = (
            self.PRODUCTION_URL 
            if config.environment == 'production' 
            else self.SANDBOX_URL
        )
        self._access_token = None
        self._token_expires = None
    
    def _get_access_token(self) -> str:
        """Get OAuth access token from M-Pesa"""
        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return self._access_token
        
        consumer_key = self.get_credential('consumer_key')
        consumer_secret = self.get_credential('consumer_secret')
        
        if not consumer_key or not consumer_secret:
            raise ValueError("M-Pesa credentials not configured")
        
        auth_string = f"{consumer_key}:{consumer_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        response = requests.get(
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth_bytes}"},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        
        data = response.json()
        self._access_token = data['access_token']
        
        # Token expires in 1 hour, we'll refresh at 50 minutes
        from datetime import timedelta
        self._token_expires = datetime.now() + timedelta(minutes=50)
        
        return self._access_token
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate the M-Pesa API password"""
        shortcode = self.get_credential('shortcode')
        passkey = self.get_credential('passkey')
        
        password_string = f"{shortcode}{passkey}{timestamp}"
        return base64.b64encode(password_string.encode()).decode()
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to 254XXXXXXXXX format"""
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        # Remove leading +
        if phone.startswith('+'):
            phone = phone[1:]
        
        # Handle 07XXXXXXXX format
        if phone.startswith('07') or phone.startswith('01'):
            phone = '254' + phone[1:]
        
        # Handle 7XXXXXXXX format
        if phone.startswith('7') or phone.startswith('1'):
            phone = '254' + phone
        
        return phone
    
    def test_connection(self) -> bool:
        """Test M-Pesa API connectivity"""
        try:
            self._get_access_token()
            return True
        except Exception as e:
            return False
    
    def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """
        Initiate STK Push (Lipa na M-Pesa Online)
        
        This sends a payment prompt to the customer's phone.
        """
        import time
        
        start_time = time.time()
        
        try:
            token = self._get_access_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            shortcode = self.get_credential('shortcode')
            password = self._generate_password(timestamp)
            phone_number = self._format_phone_number(request.phone_number)
            
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(request.amount),
                "PartyA": phone_number,
                "PartyB": shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": request.callback_url or self.config.webhook_url,
                "AccountReference": request.reference[:12] if request.reference else "Payment",
                "TransactionDesc": request.description[:13] if request.description else "Payment"
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            data = response.json()
            
            # Log the request
            self.log_request(
                action='stk_push_initiate',
                request_data={k: v for k, v in payload.items() if k != 'Password'},
                response_data=data,
                status='success' if data.get('ResponseCode') == '0' else 'failed',
                response_time_ms=elapsed_ms,
                reference_type='payment',
                reference_id=request.reference
            )
            
            if data.get('ResponseCode') == '0':
                return PaymentResult(
                    success=True,
                    transaction_id=data.get('CheckoutRequestID'),
                    provider_reference=data.get('MerchantRequestID'),
                    status='pending',
                    message='STK push sent to phone. Please enter your PIN.',
                    raw_response=data
                )
            else:
                return PaymentResult(
                    success=False,
                    status='failed',
                    message=data.get('errorMessage', data.get('ResponseDescription', 'Payment initiation failed')),
                    raw_response=data
                )
                
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            self.log_request(
                action='stk_push_initiate',
                request_data={'phone': request.phone_number, 'amount': str(request.amount)},
                response_data={},
                status='error',
                error_message=str(e),
                response_time_ms=elapsed_ms,
                reference_type='payment',
                reference_id=request.reference
            )
            
            return PaymentResult(
                success=False,
                status='error',
                message=str(e)
            )
    
    def verify_payment(self, transaction_id: str) -> PaymentResult:
        """
        Query STK Push status
        
        Use this to check if a payment was completed.
        """
        import time
        
        start_time = time.time()
        
        try:
            token = self._get_access_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            shortcode = self.get_credential('shortcode')
            password = self._generate_password(timestamp)
            
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": transaction_id
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            data = response.json()
            
            # Log the request
            self.log_request(
                action='stk_push_query',
                request_data={'checkout_request_id': transaction_id},
                response_data=data,
                status='success',
                response_time_ms=elapsed_ms,
                reference_type='payment',
                reference_id=transaction_id
            )
            
            result_code = data.get('ResultCode')
            
            if result_code == '0' or result_code == 0:
                return PaymentResult(
                    success=True,
                    transaction_id=transaction_id,
                    status='completed',
                    message='Payment completed successfully',
                    raw_response=data
                )
            elif result_code is None:
                # Still pending
                return PaymentResult(
                    success=True,
                    transaction_id=transaction_id,
                    status='pending',
                    message='Payment is still being processed',
                    raw_response=data
                )
            else:
                return PaymentResult(
                    success=False,
                    transaction_id=transaction_id,
                    status='failed',
                    message=data.get('ResultDesc', 'Payment failed'),
                    raw_response=data
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                transaction_id=transaction_id,
                status='error',
                message=str(e)
            )
    
    def process_webhook(self, payload: Dict[str, Any]) -> PaymentResult:
        """
        Process M-Pesa STK Push callback
        
        M-Pesa sends the result to this webhook when payment completes or fails.
        """
        try:
            body = payload.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            
            merchant_request_id = stk_callback.get('MerchantRequestID')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            
            if result_code == 0:
                # Payment successful
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])
                
                # Parse metadata
                metadata = {}
                for item in items:
                    name = item.get('Name')
                    value = item.get('Value')
                    if name and value is not None:
                        metadata[name] = value
                
                # Log success
                self.log_request(
                    action='stk_push_callback',
                    request_data=payload,
                    response_data={'processed': True},
                    status='success',
                    reference_type='payment',
                    reference_id=checkout_request_id
                )
                
                return PaymentResult(
                    success=True,
                    transaction_id=checkout_request_id,
                    provider_reference=metadata.get('MpesaReceiptNumber'),
                    status='completed',
                    message='Payment completed',
                    raw_response={
                        'amount': metadata.get('Amount'),
                        'receipt': metadata.get('MpesaReceiptNumber'),
                        'phone': metadata.get('PhoneNumber'),
                        'transaction_date': metadata.get('TransactionDate')
                    }
                )
            else:
                # Payment failed
                self.log_request(
                    action='stk_push_callback',
                    request_data=payload,
                    response_data={'processed': True},
                    status='failed',
                    error_message=result_desc,
                    reference_type='payment',
                    reference_id=checkout_request_id
                )
                
                return PaymentResult(
                    success=False,
                    transaction_id=checkout_request_id,
                    status='failed',
                    message=result_desc or 'Payment failed',
                    raw_response=stk_callback
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status='error',
                message=f'Webhook processing error: {str(e)}'
            )
    
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """
        M-Pesa Transaction Reversal
        
        Note: This requires additional credentials (security_credential) and
        the original transaction must be within reversal window.
        """
        # Reversal implementation would go here
        # For now, return not supported
        return PaymentResult(
            success=False,
            message='M-Pesa reversal requires additional configuration. Please contact support.'
        )
