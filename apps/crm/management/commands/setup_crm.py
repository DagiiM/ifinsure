"""
Management command to set up initial CRM data.
Creates insurance providers, product categories, and sample products.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.crm.models import (
    InsuranceProvider, ProductCategory, InsuranceProduct, ProductBenefit
)


class Command(BaseCommand):
    help = 'Set up initial CRM data (providers, categories, products)'
    
    def handle(self, *args, **options):
        self.setup_providers()
        self.setup_categories()
        self.setup_products()
        self.stdout.write(self.style.SUCCESS('\nCRM setup complete!'))
    
    def setup_providers(self):
        """Create insurance provider companies."""
        providers = [
            {
                'name': 'Britam Insurance',
                'code': 'BRITAM',
                'provider_type': 'underwriter',
                'email': 'info@britam.com',
                'phone': '+254 703 094 000',
                'website': 'https://www.britam.com',
                'address': 'Britam Tower, Upper Hill, Nairobi',
                'city': 'Nairobi',
                'registration_number': 'PVT-ABDCXY1234',
                'ira_license': 'IRA/UW/001',
                'default_commission_rate': Decimal('12.50'),
                'primary_color': '#1e40af',
            },
            {
                'name': 'Jubilee Insurance',
                'code': 'JUBILEE',
                'provider_type': 'underwriter',
                'email': 'info@jubilee.co.ke',
                'phone': '+254 709 949 000',
                'website': 'https://www.jubileeinsurance.com',
                'address': 'Jubilee Insurance House, Wabera Street',
                'city': 'Nairobi',
                'ira_license': 'IRA/UW/002',
                'default_commission_rate': Decimal('10.00'),
                'primary_color': '#b91c1c',
            },
            {
                'name': 'UAP Old Mutual',
                'code': 'UAP',
                'provider_type': 'underwriter',
                'email': 'info@uap-group.com',
                'phone': '+254 711 065 100',
                'website': 'https://www.oldmutual.co.ke',
                'address': 'UAP Old Mutual Tower, Upper Hill',
                'city': 'Nairobi',
                'ira_license': 'IRA/UW/003',
                'default_commission_rate': Decimal('10.00'),
                'primary_color': '#166534',
            },
            {
                'name': 'APA Insurance',
                'code': 'APA',
                'provider_type': 'underwriter',
                'email': 'info@apainsurance.org',
                'phone': '+254 020 286 4000',
                'website': 'https://www.apainsurance.org',
                'address': 'Apollo Centre, Ring Road Parklands',
                'city': 'Nairobi',
                'ira_license': 'IRA/UW/004',
                'default_commission_rate': Decimal('12.00'),
                'primary_color': '#ea580c',
            },
            {
                'name': 'CIC Insurance',
                'code': 'CIC',
                'provider_type': 'underwriter',
                'email': 'info@cic.co.ke',
                'phone': '+254 722 099 803',
                'website': 'https://www.cic.co.ke',
                'address': 'CIC Plaza, Mara Road',
                'city': 'Nairobi',
                'ira_license': 'IRA/UW/005',
                'default_commission_rate': Decimal('10.00'),
                'primary_color': '#0891b2',
            },
            {
                'name': 'Madison Insurance',
                'code': 'MADISON',
                'provider_type': 'underwriter',
                'email': 'info@madison.co.ke',
                'phone': '+254 20 286 7000',
                'website': 'https://www.madison.co.ke',
                'address': 'Madison House, Upper Hill Close',
                'city': 'Nairobi',
                'ira_license': 'IRA/UW/006',
                'default_commission_rate': Decimal('12.00'),
                'primary_color': '#7c3aed',
            },
        ]
        
        for provider_data in providers:
            provider, created = InsuranceProvider.objects.update_or_create(
                code=provider_data['code'],
                defaults=provider_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created provider: {provider.name}'))
            else:
                self.stdout.write(f'Updated provider: {provider.name}')
    
    def setup_categories(self):
        """Create product categories."""
        categories = [
            {'name': 'Motor', 'code': 'MOTOR', 'icon': 'car', 'display_order': 1},
            {'name': 'Health', 'code': 'HEALTH', 'icon': 'heart', 'display_order': 2},
            {'name': 'Life', 'code': 'LIFE', 'icon': 'shield', 'display_order': 3},
            {'name': 'Property', 'code': 'PROPERTY', 'icon': 'home', 'display_order': 4},
            {'name': 'Travel', 'code': 'TRAVEL', 'icon': 'plane', 'display_order': 5},
            {'name': 'Personal Accident', 'code': 'PA', 'icon': 'user', 'display_order': 6},
            {'name': 'Marine', 'code': 'MARINE', 'icon': 'ship', 'display_order': 7},
            {'name': 'Engineering', 'code': 'ENGINEERING', 'icon': 'tool', 'display_order': 8},
            {'name': 'Liability', 'code': 'LIABILITY', 'icon': 'briefcase', 'display_order': 9},
        ]
        
        for cat_data in categories:
            cat, created = ProductCategory.objects.update_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat.name}'))
    
    def setup_products(self):
        """Create sample insurance products."""
        motor = ProductCategory.objects.get(code='MOTOR')
        health = ProductCategory.objects.get(code='HEALTH')
        life = ProductCategory.objects.get(code='LIFE')
        travel = ProductCategory.objects.get(code='TRAVEL')
        
        britam = InsuranceProvider.objects.get(code='BRITAM')
        jubilee = InsuranceProvider.objects.get(code='JUBILEE')
        apa = InsuranceProvider.objects.get(code='APA')
        cic = InsuranceProvider.objects.get(code='CIC')
        
        products = [
            # Motor Products
            {
                'provider': britam,
                'category': motor,
                'name': 'Britam Motor Comprehensive',
                'code': 'BRITAM-MOTOR-COMP',
                'short_description': 'Full coverage for your vehicle',
                'description': 'Comprehensive motor insurance covering own damage, third party liability, and more.',
                'premium_type': 'percentage',
                'base_premium': Decimal('4.50'),
                'min_premium': Decimal('25000'),
                'commission_rate': Decimal('12.50'),
                'featured': True,
                'benefits': [
                    ('Own Vehicle Damage', 'Full value of vehicle', True),
                    ('Third Party Liability', 'Up to KES 3,000,000', True),
                    ('Windscreen Cover', 'Up to KES 50,000', True),
                    ('Personal Accident', 'Up to KES 500,000', True),
                    ('Roadside Rescue', '24/7 assistance', True),
                ]
            },
            {
                'provider': jubilee,
                'category': motor,
                'name': 'Jubilee Motor Third Party Only',
                'code': 'JUB-MOTOR-TPO',
                'short_description': 'Essential third party cover',
                'description': 'Covers your liability to third parties for bodily injury and property damage.',
                'premium_type': 'fixed',
                'base_premium': Decimal('7500'),
                'min_premium': Decimal('7500'),
                'commission_rate': Decimal('10.00'),
                'benefits': [
                    ('Third Party Bodily Injury', 'Unlimited', True),
                    ('Third Party Property Damage', 'Up to KES 3,000,000', True),
                ]
            },
            {
                'provider': apa,
                'category': motor,
                'name': 'APA Motor Comprehensive Plus',
                'code': 'APA-MOTOR-PLUS',
                'short_description': 'Premium protection for your vehicle',
                'description': 'Enhanced comprehensive cover with additional benefits.',
                'premium_type': 'percentage',
                'base_premium': Decimal('5.00'),
                'min_premium': Decimal('30000'),
                'commission_rate': Decimal('12.00'),
                'featured': True,
                'benefits': [
                    ('Own Vehicle Damage', 'Full market value', True),
                    ('Third Party Liability', 'Up to KES 5,000,000', True),
                    ('Political Violence & Terrorism', 'Included', True),
                    ('Excess Protector', 'Zero excess on first claim', True),
                ]
            },
            # Health Products
            {
                'provider': britam,
                'category': health,
                'name': 'Britam Health Individual',
                'code': 'BRITAM-HEALTH-IND',
                'short_description': 'Comprehensive health cover for individuals',
                'description': 'Inpatient and outpatient cover for you and your family.',
                'premium_type': 'fixed',
                'base_premium': Decimal('45000'),
                'min_premium': Decimal('45000'),
                'commission_rate': Decimal('15.00'),
                'featured': True,
                'benefits': [
                    ('Inpatient Cover', 'Up to KES 2,000,000', True),
                    ('Outpatient Cover', 'Up to KES 100,000', True),
                    ('Maternity Cover', 'Up to KES 150,000', False),
                    ('Dental Cover', 'Up to KES 30,000', False),
                ]
            },
            {
                'provider': jubilee,
                'category': health,
                'name': 'Jubilee AfyaImara',
                'code': 'JUB-AFYAIMARA',
                'short_description': 'Affordable health insurance',
                'description': 'Budget-friendly health cover with essential benefits.',
                'premium_type': 'fixed',
                'base_premium': Decimal('18000'),
                'min_premium': Decimal('18000'),
                'commission_rate': Decimal('12.00'),
                'benefits': [
                    ('Inpatient Cover', 'Up to KES 500,000', True),
                    ('Outpatient Cover', 'Up to KES 50,000', True),
                ]
            },
            # Life Products
            {
                'provider': cic,
                'category': life,
                'name': 'CIC Term Life',
                'code': 'CIC-TERM-LIFE',
                'short_description': 'Pure life protection',
                'description': 'Term life insurance providing financial security for your loved ones.',
                'premium_type': 'calculated',
                'base_premium': Decimal('0'),
                'min_premium': Decimal('5000'),
                'commission_rate': Decimal('25.00'),
                'benefits': [
                    ('Death Benefit', 'Sum assured on death', True),
                    ('Terminal Illness', 'Accelerated benefit', True),
                ]
            },
            # Travel Products
            {
                'provider': apa,
                'category': travel,
                'name': 'APA Travel Guard',
                'code': 'APA-TRAVEL',
                'short_description': 'International travel protection',
                'description': 'Comprehensive travel insurance for trips abroad.',
                'premium_type': 'fixed',
                'base_premium': Decimal('2500'),
                'min_premium': Decimal('2500'),
                'default_duration_months': 1,
                'commission_rate': Decimal('20.00'),
                'featured': True,
                'benefits': [
                    ('Emergency Medical', 'Up to USD 100,000', True),
                    ('Trip Cancellation', 'Up to USD 5,000', True),
                    ('Lost Baggage', 'Up to USD 1,500', True),
                    ('Flight Delay', 'USD 50 per 6 hours', True),
                ]
            },
        ]
        
        for product_data in products:
            benefits = product_data.pop('benefits', [])
            
            product, created = InsuranceProduct.objects.update_or_create(
                code=product_data['code'],
                defaults=product_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
                
                # Create benefits
                for i, (name, coverage, included) in enumerate(benefits):
                    ProductBenefit.objects.create(
                        product=product,
                        name=name,
                        coverage_description=coverage,
                        is_included=included,
                        display_order=i
                    )
            else:
                self.stdout.write(f'Updated product: {product.name}')
