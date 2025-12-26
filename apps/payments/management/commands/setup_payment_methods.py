"""
Management command to set up initial payment methods.
"""
from django.core.management.base import BaseCommand
from apps.payments.models import PaymentMethod, PaymentAccount


class Command(BaseCommand):
    help = 'Set up initial payment methods'
    
    def handle(self, *args, **options):
        # Create payment methods
        methods = [
            {
                'name': 'M-Pesa',
                'code': 'mpesa',
                'method_type': 'mpesa',
                'description': 'Pay instantly via M-Pesa STK Push',
                'requires_proof': False,  # STK Push - automatic
                'min_amount': 10,
                'max_amount': 150000,
                'icon': 'phone',
                'display_order': 1,
                'is_active': True,
                'instructions': '''
1. Enter your M-Pesa phone number
2. Click "Pay Now"
3. You will receive an STK push on your phone
4. Enter your M-Pesa PIN to complete payment
5. Your wallet will be credited automatically
                '''.strip(),
                'payment_details_schema': {
                    'type': 'object',
                    'required': ['phone_number'],
                    'properties': {
                        'phone_number': {
                            'type': 'string',
                            'title': 'M-Pesa Phone Number',
                            'pattern': '^254[0-9]{9}$',
                            'description': 'Format: 254XXXXXXXXX'
                        }
                    }
                },
                'provider_config': {
                    'provider': 'safaricom',
                    'type': 'stk_push',
                    'business_shortcode': '174379',
                    'account_reference': 'ifinsure'
                }
            },
            {
                'name': 'Bank Transfer',
                'code': 'bank_transfer',
                'method_type': 'p2p',
                'description': 'Transfer via bank and upload proof',
                'requires_proof': True,  # P2P - needs proof
                'min_amount': 500,
                'icon': 'building-2',
                'display_order': 2,
                'is_active': True,
                'instructions': '''
1. Log in to your bank's mobile or internet banking
2. Transfer to the account details shown
3. Use your payment reference as the description
4. Take a screenshot of the confirmation
5. Upload the screenshot as proof of payment
6. Your wallet will be credited after verification
                '''.strip(),
                'payment_details_schema': {
                    'type': 'object',
                    'properties': {
                        'bank_name': {
                            'type': 'string',
                            'title': 'Your Bank'
                        }
                    }
                }
            },
        ]
        
        # Disable old methods
        PaymentMethod.objects.filter(code__in=['card', 'paypal']).update(is_active=False)
        
        created_count = 0
        updated_count = 0
        
        for method_data in methods:
            method, created = PaymentMethod.objects.update_or_create(
                code=method_data['code'],
                defaults=method_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created payment method: {method.name}'))
            else:
                updated_count += 1
                self.stdout.write(f'Updated payment method: {method.name}')
        
        # Create bank accounts for P2P
        bank = PaymentMethod.objects.get(code='bank_transfer')
        bank_accounts = [
            {
                'payment_method': bank,
                'name': 'Equity Bank',
                'account_details': {
                    'type': 'bank',
                    'bank_name': 'Equity Bank',
                    'account_name': 'ifinsure Insurance Ltd',
                    'account_number': '1234567890123',
                    'branch': 'Westlands'
                },
                'display_order': 1
            },
            {
                'payment_method': bank,
                'name': 'KCB Bank',
                'account_details': {
                    'type': 'bank',
                    'bank_name': 'KCB Bank',
                    'account_name': 'ifinsure Insurance Ltd',
                    'account_number': '9876543210123',
                    'branch': 'Nairobi CBD'
                },
                'display_order': 2
            },
        ]
        
        for account_data in bank_accounts:
            account, created = PaymentAccount.objects.update_or_create(
                name=account_data['name'],
                payment_method=account_data['payment_method'],
                defaults=account_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created payment account: {account.name}'))
            else:
                self.stdout.write(f'Updated payment account: {account.name}')
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSummary: {created_count} created, {updated_count} updated'
        ))
        self.stdout.write(self.style.SUCCESS('Card/PayPal methods disabled'))
