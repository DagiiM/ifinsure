"""
Management command to seed integration data.
Creates default categories and providers.
"""
from django.core.management.base import BaseCommand
from apps.integrations.models import IntegrationCategory, IntegrationProvider


class Command(BaseCommand):
    help = 'Seeds the database with default integration categories and providers'
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding integration data...')
        
        # Create categories
        categories_data = [
            {
                'name': 'payment',
                'slug': 'payment',
                'description': 'Payment gateways and processors for accepting customer payments',
                'icon': '💳',
                'display_order': 1
            },
            {
                'name': 'sms',
                'slug': 'sms',
                'description': 'SMS gateways for sending notifications and alerts to customers',
                'icon': '📱',
                'display_order': 2
            },
            {
                'name': 'email',
                'slug': 'email',
                'description': 'Email service providers for transactional and marketing emails',
                'icon': '📧',
                'display_order': 3
            },
            {
                'name': 'storage',
                'slug': 'storage',
                'description': 'Cloud storage services for documents and media files',
                'icon': '☁️',
                'display_order': 4
            },
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = IntegrationCategory.objects.update_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            categories[cat_data['name']] = cat
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status} category: {cat.get_name_display()}')
        
        # Create providers
        providers_data = [
            # Payment Providers
            {
                'category': 'payment',
                'name': 'M-Pesa',
                'slug': 'mpesa',
                'description': 'Safaricom M-Pesa mobile money integration via Daraja API. Supports STK Push, C2B, and B2C transactions.',
                'website_url': 'https://developer.safaricom.co.ke/',
                'documentation_url': 'https://developer.safaricom.co.ke/APIs',
                'provider_class': 'apps.integrations.providers.payments.mpesa.MPesaProvider',
                'supports_webhooks': True,
                'supports_sandbox': True,
                'supports_refunds': True,
                'countries': ['KE'],
                'config_schema': {
                    'consumer_key': {
                        'type': 'password',
                        'required': True,
                        'label': 'Consumer Key',
                        'help_text': 'Your M-Pesa API Consumer Key from Daraja portal'
                    },
                    'consumer_secret': {
                        'type': 'password',
                        'required': True,
                        'label': 'Consumer Secret',
                        'help_text': 'Your M-Pesa API Consumer Secret from Daraja portal'
                    },
                    'shortcode': {
                        'type': 'text',
                        'required': True,
                        'label': 'Business Shortcode',
                        'placeholder': '174379',
                        'help_text': 'Your Paybill or Till number'
                    },
                    'passkey': {
                        'type': 'password',
                        'required': True,
                        'label': 'Passkey',
                        'help_text': 'The Lipa na M-Pesa passkey'
                    }
                }
            },
            {
                'category': 'payment',
                'name': 'Stripe',
                'slug': 'stripe',
                'description': 'Global payment processing for credit cards and alternative payment methods.',
                'website_url': 'https://stripe.com/',
                'documentation_url': 'https://stripe.com/docs',
                'provider_class': 'apps.integrations.providers.payments.stripe.StripeProvider',
                'supports_webhooks': True,
                'supports_sandbox': True,
                'supports_refunds': True,
                'countries': ['US', 'GB', 'EU', 'AU', 'CA'],
                'config_schema': {
                    'public_key': {
                        'type': 'text',
                        'required': True,
                        'label': 'Publishable Key',
                        'placeholder': 'pk_test_...'
                    },
                    'secret_key': {
                        'type': 'password',
                        'required': True,
                        'label': 'Secret Key',
                        'placeholder': 'sk_test_...'
                    },
                    'webhook_secret': {
                        'type': 'password',
                        'required': False,
                        'label': 'Webhook Signing Secret',
                        'placeholder': 'whsec_...'
                    }
                }
            },
            {
                'category': 'payment',
                'name': 'PayStack',
                'slug': 'paystack',
                'description': 'African payment gateway supporting cards, bank transfers, and mobile money.',
                'website_url': 'https://paystack.com/',
                'documentation_url': 'https://paystack.com/docs/',
                'provider_class': 'apps.integrations.providers.payments.paystack.PayStackProvider',
                'supports_webhooks': True,
                'supports_sandbox': True,
                'supports_refunds': True,
                'countries': ['NG', 'GH', 'ZA', 'KE'],
                'config_schema': {
                    'public_key': {
                        'type': 'text',
                        'required': True,
                        'label': 'Public Key'
                    },
                    'secret_key': {
                        'type': 'password',
                        'required': True,
                        'label': 'Secret Key'
                    }
                }
            },
            # SMS Providers
            {
                'category': 'sms',
                'name': "Africa's Talking",
                'slug': 'africastalking',
                'description': 'Pan-African communication APIs for SMS, voice, and USSD.',
                'website_url': 'https://africastalking.com/',
                'documentation_url': 'https://developers.africastalking.com/',
                'provider_class': 'apps.integrations.providers.sms.africastalking.AfricasTalkingProvider',
                'supports_webhooks': True,
                'supports_sandbox': True,
                'countries': ['KE', 'UG', 'TZ', 'NG', 'RW'],
                'config_schema': {
                    'username': {
                        'type': 'text',
                        'required': True,
                        'label': 'Username'
                    },
                    'api_key': {
                        'type': 'password',
                        'required': True,
                        'label': 'API Key'
                    },
                    'sender_id': {
                        'type': 'text',
                        'required': False,
                        'label': 'Sender ID',
                        'placeholder': 'ifinsure'
                    }
                }
            },
            {
                'category': 'sms',
                'name': 'Twilio',
                'slug': 'twilio',
                'description': 'Global cloud communications platform for SMS, voice, and messaging.',
                'website_url': 'https://twilio.com/',
                'documentation_url': 'https://www.twilio.com/docs',
                'provider_class': 'apps.integrations.providers.sms.twilio.TwilioProvider',
                'supports_webhooks': True,
                'supports_sandbox': True,
                'countries': ['US', 'GB', 'CA', 'AU', 'KE'],
                'config_schema': {
                    'account_sid': {
                        'type': 'text',
                        'required': True,
                        'label': 'Account SID'
                    },
                    'auth_token': {
                        'type': 'password',
                        'required': True,
                        'label': 'Auth Token'
                    },
                    'phone_number': {
                        'type': 'text',
                        'required': True,
                        'label': 'Twilio Phone Number',
                        'placeholder': '+1234567890'
                    }
                }
            },
            # Email Providers
            {
                'category': 'email',
                'name': 'SMTP',
                'slug': 'smtp',
                'description': 'Standard SMTP email configuration for any email provider.',
                'website_url': '',
                'documentation_url': '',
                'provider_class': 'apps.integrations.providers.email.smtp.SMTPProvider',
                'supports_webhooks': False,
                'supports_sandbox': False,
                'countries': [],
                'config_schema': {
                    'host': {
                        'type': 'text',
                        'required': True,
                        'label': 'SMTP Host',
                        'placeholder': 'smtp.gmail.com'
                    },
                    'port': {
                        'type': 'text',
                        'required': True,
                        'label': 'SMTP Port',
                        'placeholder': '587'
                    },
                    'username': {
                        'type': 'text',
                        'required': True,
                        'label': 'Username'
                    },
                    'password': {
                        'type': 'password',
                        'required': True,
                        'label': 'Password'
                    },
                    'use_tls': {
                        'type': 'checkbox',
                        'required': False,
                        'label': 'Use TLS'
                    }
                }
            },
            {
                'category': 'email',
                'name': 'SendGrid',
                'slug': 'sendgrid',
                'description': 'Cloud-based email delivery platform with templates and analytics.',
                'website_url': 'https://sendgrid.com/',
                'documentation_url': 'https://docs.sendgrid.com/',
                'provider_class': 'apps.integrations.providers.email.sendgrid.SendGridProvider',
                'supports_webhooks': True,
                'supports_sandbox': True,
                'countries': [],
                'config_schema': {
                    'api_key': {
                        'type': 'password',
                        'required': True,
                        'label': 'API Key',
                        'placeholder': 'SG.xxx'
                    },
                    'from_email': {
                        'type': 'text',
                        'required': True,
                        'label': 'From Email',
                        'placeholder': 'noreply@ifinsure.com'
                    },
                    'from_name': {
                        'type': 'text',
                        'required': False,
                        'label': 'From Name',
                        'placeholder': 'ifinsure'
                    }
                }
            },
            # Storage Providers
            {
                'category': 'storage',
                'name': 'Amazon S3',
                'slug': 'aws-s3',
                'description': 'Amazon Web Services Simple Storage Service for scalable file storage.',
                'website_url': 'https://aws.amazon.com/s3/',
                'documentation_url': 'https://docs.aws.amazon.com/s3/',
                'provider_class': 'apps.integrations.providers.storage.s3.S3Provider',
                'supports_webhooks': False,
                'supports_sandbox': False,
                'countries': [],
                'config_schema': {
                    'access_key_id': {
                        'type': 'text',
                        'required': True,
                        'label': 'Access Key ID'
                    },
                    'secret_access_key': {
                        'type': 'password',
                        'required': True,
                        'label': 'Secret Access Key'
                    },
                    'bucket_name': {
                        'type': 'text',
                        'required': True,
                        'label': 'Bucket Name'
                    },
                    'region': {
                        'type': 'text',
                        'required': True,
                        'label': 'Region',
                        'placeholder': 'us-east-1'
                    }
                }
            },
        ]
        
        for prov_data in providers_data:
            category = categories.get(prov_data.pop('category'))
            if not category:
                continue
            
            provider, created = IntegrationProvider.objects.update_or_create(
                slug=prov_data['slug'],
                defaults={**prov_data, 'category': category}
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status} provider: {provider.name}')
        
        self.stdout.write(self.style.SUCCESS('\nIntegration data seeded successfully!'))
