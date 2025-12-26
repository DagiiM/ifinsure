"""
Landing page models for dynamic content management.
"""
from django.db import models
from apps.core.models import BaseModel, SimpleBaseModel


class LandingPageSettings(SimpleBaseModel):
    """
    Singleton model for landing page hero section and global settings.
    """
    # Hero Section
    hero_badge_text = models.CharField(
        max_length=50,
        default="Next Gen Insurance",
        help_text="Badge text above the title"
    )
    hero_title = models.CharField(
        max_length=200,
        default="Insurance Simplified for Modern Business"
    )
    hero_subtitle = models.TextField(
        default="Experience lightning-fast claims, transparent policies, and specific coverage tailored for your growth. No paperwork, just protection."
    )
    hero_cta_primary_text = models.CharField(
        max_length=50,
        default="Start Free Trial"
    )
    hero_cta_secondary_text = models.CharField(
        max_length=50,
        default="Learn More"
    )
    hero_feature_1 = models.CharField(
        max_length=50,
        default="Instant Approval"
    )
    hero_feature_2 = models.CharField(
        max_length=50,
        default="24/7 Support"
    )
    
    # Dashboard Card Demo
    demo_coverage_amount = models.CharField(
        max_length=50,
        default="KES 50,000,000"
    )
    demo_growth_percentage = models.CharField(
        max_length=20,
        default="+12.5%"
    )
    demo_policies_count = models.CharField(
        max_length=20,
        default="1,234"
    )
    demo_claims_rate = models.CharField(
        max_length=20,
        default="98%"
    )
    
    # Trusted By Section
    trusted_by_text = models.CharField(
        max_length=100,
        default="Trusted by over 2,000 modern companies"
    )
    
    # Features Section
    features_title = models.CharField(
        max_length=100,
        default="Why Choose ifinsure?"
    )
    features_subtitle = models.TextField(
        default="We've reimagined insurance from the ground up to serve the speed of modern business."
    )
    
    # Process Section
    process_title = models.CharField(
        max_length=100,
        default="Insurance in 3 Simple Steps"
    )
    process_step_1_title = models.CharField(max_length=50, default="Apply Online")
    process_step_1_description = models.TextField(
        default="Fill out a simple, smart form to tell us about your business needs in under 5 minutes."
    )
    process_step_2_title = models.CharField(max_length=50, default="Get Approved")
    process_step_2_description = models.TextField(
        default="Our AI reviews your application instantly, generating a custom quote and immediate coverage."
    )
    process_step_3_title = models.CharField(max_length=50, default="Manage Policy")
    process_step_3_description = models.TextField(
        default="Access your state-of-the-art dashboard to file claims, adjust coverage, and pay premiums 24/7."
    )
    
    # Testimonials Section
    testimonials_title = models.CharField(
        max_length=100,
        default="Loved by Businesses Everywhere"
    )
    testimonials_subtitle = models.TextField(
        default="See what our customers have to say about their experience with ifinsure."
    )
    
    # FAQ Section
    faq_title = models.CharField(
        max_length=100,
        default="Frequently Asked Questions"
    )
    faq_subtitle = models.TextField(
        default="Everything you need to know about ifinsure."
    )
    
    # CTA Section
    cta_title = models.CharField(
        max_length=100,
        default="Ready to secure your future?"
    )
    cta_subtitle = models.TextField(
        default="Join thousands of businesses trusting ifinsure today."
    )
    cta_button_text = models.CharField(
        max_length=50,
        default="Get Started"
    )
    cta_disclaimer = models.CharField(
        max_length=200,
        default="No credit card required. Start your free trial today."
    )
    
    # Floating CTA
    floating_cta_text = models.CharField(
        max_length=50,
        default="Get Protected"
    )
    
    class Meta:
        verbose_name = "Landing Page Settings"
        verbose_name_plural = "Landing Page Settings"
    
    def __str__(self):
        return "Landing Page Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton)
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class LandingFeature(SimpleBaseModel):
    """
    Feature cards for the landing page.
    """
    ICON_CHOICES = [
        ('lightning', 'Lightning Bolt'),
        ('grid', 'Grid/Dashboard'),
        ('shield', 'Shield'),
        ('clock', 'Clock'),
        ('cube', 'Cube/3D'),
        ('chart', 'Chart'),
        ('users', 'Users'),
        ('document', 'Document'),
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='shield')
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Landing Feature"
        verbose_name_plural = "Landing Features"
    
    def __str__(self):
        return self.title


class LandingStat(SimpleBaseModel):
    """
    Statistics displayed on the landing page.
    """
    value = models.CharField(max_length=20, help_text="e.g., '2M+', '98%', '24/7'")
    label = models.CharField(max_length=50, help_text="e.g., 'Active Policies'")
    order = models.PositiveIntegerField(default=0)
    # For animated counters
    is_animated = models.BooleanField(default=True)
    numeric_value = models.IntegerField(
        null=True,
        blank=True,
        help_text="Numeric value for animation (e.g., 2 for '2M+')"
    )
    suffix = models.CharField(
        max_length=10,
        blank=True,
        help_text="Suffix for animation (e.g., 'M+', '%')"
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "Landing Statistic"
        verbose_name_plural = "Landing Statistics"
    
    def __str__(self):
        return f"{self.value} - {self.label}"


class LandingTestimonial(SimpleBaseModel):
    """
    Customer testimonials for the landing page.
    """
    quote = models.TextField()
    author_name = models.CharField(max_length=100)
    author_title = models.CharField(max_length=100, help_text="e.g., 'CEO, TechCorp'")
    author_initials = models.CharField(
        max_length=3,
        help_text="Initials for avatar (e.g., 'JM')"
    )
    rating = models.PositiveIntegerField(
        default=5,
        help_text="Star rating (1-5)"
    )
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Landing Testimonial"
        verbose_name_plural = "Landing Testimonials"
    
    def __str__(self):
        return f"{self.author_name} - {self.author_title}"


class LandingFAQ(SimpleBaseModel):
    """
    FAQ items for the landing page.
    """
    question = models.CharField(max_length=200)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Landing FAQ"
        verbose_name_plural = "Landing FAQs"
    
    def __str__(self):
        return self.question


class LandingTrustedCompany(SimpleBaseModel):
    """
    Company logos for "Trusted By" section.
    """
    name = models.CharField(max_length=100)
    # SVG code for the logo (inline)
    svg_code = models.TextField(
        help_text="SVG code for the company logo",
        blank=True
    )
    # Or URL to logo image
    logo_url = models.URLField(blank=True, help_text="URL to logo image (alternative to SVG)")
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Trusted Company"
        verbose_name_plural = "Trusted Companies"
    
    def __str__(self):
        return self.name


class UserReview(BaseModel):
    """
    Customer-submitted reviews that are moderated before appearing on landing page.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    quote = models.TextField(
        help_text="Your review/testimonial"
    )
    rating = models.PositiveIntegerField(
        default=5,
        help_text="Rating (1-5 stars)"
    )
    
    # Moderation
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Display preferences
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name to display (leave blank to use account name)"
    )
    display_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Title to display (e.g., 'CEO, TechCorp')"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Review"
        verbose_name_plural = "User Reviews"
    
    def __str__(self):
        return f"Review by {self.user.get_full_name() or self.user.email} - {self.status}"
    
    @property
    def author_name(self):
        """Get display name."""
        if self.display_name:
            return self.display_name
        return self.user.get_full_name() or self.user.email.split('@')[0]
    
    @property
    def author_initials(self):
        """Get initials for avatar."""
        name = self.author_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()
    
    @property
    def author_title(self):
        """Get display title."""
        if self.display_title:
            return self.display_title
        return "ifinsure Customer"
    
    def approve(self, moderator):
        """Approve the review."""
        from django.utils import timezone
        self.status = 'approved'
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        self.save()
    
    def reject(self, moderator, reason=''):
        """Reject the review."""
        from django.utils import timezone
        self.status = 'rejected'
        self.reviewed_by = moderator
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()
