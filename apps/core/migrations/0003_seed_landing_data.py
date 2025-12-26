"""
Seed initial landing page data.
"""
from django.db import migrations


def seed_landing_data(apps, schema_editor):
    """Seed initial landing page content."""
    LandingPageSettings = apps.get_model('core', 'LandingPageSettings')
    LandingFeature = apps.get_model('core', 'LandingFeature')
    LandingStat = apps.get_model('core', 'LandingStat')
    LandingTestimonial = apps.get_model('core', 'LandingTestimonial')
    LandingFAQ = apps.get_model('core', 'LandingFAQ')
    LandingTrustedCompany = apps.get_model('core', 'LandingTrustedCompany')
    
    # Create default settings
    LandingPageSettings.objects.get_or_create(pk=1)
    
    # Create features
    features = [
        {
            'title': 'Instant Quotes',
            'description': 'Get a quote in seconds, not days. Our AI-driven algorithms assess risk instantly to give you the best rates.',
            'icon': 'lightning',
            'order': 1,
        },
        {
            'title': 'Digital First',
            'description': 'Manage everything from your dashboard. File claims, adjust coverage, and pay premiums with a click.',
            'icon': 'grid',
            'order': 2,
        },
        {
            'title': 'Comprehensive Coverage',
            'description': 'From liability to property, we cover every aspect of your business with tailored policies.',
            'icon': 'shield',
            'order': 3,
        },
        {
            'title': '24/7 Claims Support',
            'description': 'File claims anytime. Our dedicated team processes requests around the clock for faster resolutions.',
            'icon': 'clock',
            'order': 4,
        },
        {
            'title': 'Smart Analytics',
            'description': 'Get insights into your coverage, claims history, and risk profile with our intelligent dashboard.',
            'icon': 'cube',
            'order': 5,
        },
    ]
    for feature in features:
        LandingFeature.objects.get_or_create(
            title=feature['title'],
            defaults=feature
        )
    
    # Create stats
    stats = [
        {'value': '2M+', 'label': 'Active Policies', 'numeric_value': 2, 'suffix': 'M+', 'order': 1},
        {'value': '98%', 'label': 'Claims Approved', 'numeric_value': 98, 'suffix': '%', 'order': 2},
        {'value': '24/7', 'label': 'Support Available', 'numeric_value': None, 'suffix': '', 'order': 3, 'is_animated': False},
        {'value': '15m', 'label': 'Avg Payout Time', 'numeric_value': 15, 'suffix': 'm', 'order': 4},
    ]
    for stat in stats:
        LandingStat.objects.get_or_create(
            label=stat['label'],
            defaults=stat
        )
    
    # Create testimonials
    testimonials = [
        {
            'quote': 'ifinsure transformed how we manage our business insurance. The dashboard is intuitive, and claims are processed incredibly fast.',
            'author_name': 'James Mwangi',
            'author_title': 'CEO, TechVentures Ltd',
            'author_initials': 'JM',
            'rating': 5,
            'order': 1,
        },
        {
            'quote': 'We saved 30% on our premiums by switching to ifinsure. The AI-powered quotes are amazingly accurate and competitive.',
            'author_name': 'Amina Karanja',
            'author_title': 'Founder, GreenLogistics',
            'author_initials': 'AK',
            'rating': 5,
            'order': 2,
        },
        {
            'quote': 'The 24/7 support is a game-changer. Had a claim processed over the weekend in just a few hours. Truly modern insurance.',
            'author_name': 'David Ochieng',
            'author_title': 'MD, SafariTours Kenya',
            'author_initials': 'DO',
            'rating': 5,
            'order': 3,
        },
    ]
    for testimonial in testimonials:
        LandingTestimonial.objects.get_or_create(
            author_name=testimonial['author_name'],
            defaults=testimonial
        )
    
    # Create FAQs
    faqs = [
        {
            'question': 'How quickly can I get a quote?',
            'answer': 'Our AI-powered system generates quotes in under 60 seconds. Simply fill out our smart form with your business details, and you\'ll receive a comprehensive quote instantly.',
            'order': 1,
        },
        {
            'question': 'What types of insurance do you offer?',
            'answer': 'We offer comprehensive business insurance including General Liability, Property Insurance, Professional Liability, Workers\' Compensation, Cyber Insurance, and customized industry-specific policies.',
            'order': 2,
        },
        {
            'question': 'How do I file a claim?',
            'answer': 'Filing a claim is simple. Log into your dashboard, click "File a Claim," upload any relevant documents, and submit. Our team reviews claims 24/7, with most processed within 24-48 hours.',
            'order': 3,
        },
        {
            'question': 'Can I cancel my policy anytime?',
            'answer': 'Yes, you can cancel your policy at any time. We offer flexible terms with no hidden cancellation fees. Any unused premium will be refunded on a pro-rata basis.',
            'order': 4,
        },
    ]
    for faq in faqs:
        LandingFAQ.objects.get_or_create(
            question=faq['question'],
            defaults=faq
        )
    
    # Create trusted companies
    companies = [
        {'name': 'TechCorp', 'order': 1},
        {'name': 'FinanceHub', 'order': 2},
        {'name': 'GlobalTrade', 'order': 3},
        {'name': 'InnovateCo', 'order': 4},
        {'name': 'STRATOS', 'order': 5},
    ]
    for company in companies:
        LandingTrustedCompany.objects.get_or_create(
            name=company['name'],
            defaults=company
        )


def reverse_seed(apps, schema_editor):
    """Reverse the seeding (optional)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_landing_page_models'),
    ]

    operations = [
        migrations.RunPython(seed_landing_data, reverse_seed),
    ]
