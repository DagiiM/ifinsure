"""
Core admin configuration.
"""
from django.contrib import admin
from apps.core.models import AuditLog
from apps.core.landing_models import (
    LandingPageSettings,
    LandingFeature,
    LandingStat,
    LandingTestimonial,
    LandingFAQ,
    LandingTrustedCompany,
    UserReview,
)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for AuditLog."""
    list_display = ['created_at', 'user', 'action', 'model_name', 'object_repr']
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['user__email', 'object_repr', 'ip_address']
    readonly_fields = [
        'user', 'action', 'model_name', 'object_id', 'object_repr',
        'changes', 'ip_address', 'user_agent', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(LandingPageSettings)
class LandingPageSettingsAdmin(admin.ModelAdmin):
    """Admin for landing page global settings."""
    
    fieldsets = (
        ('Hero Section', {
            'fields': (
                'hero_badge_text',
                'hero_title',
                'hero_subtitle',
                'hero_cta_primary_text',
                'hero_cta_secondary_text',
                'hero_feature_1',
                'hero_feature_2',
            )
        }),
        ('Dashboard Demo Card', {
            'fields': (
                'demo_coverage_amount',
                'demo_growth_percentage',
                'demo_policies_count',
                'demo_claims_rate',
            )
        }),
        ('Trusted By Section', {
            'fields': ('trusted_by_text',)
        }),
        ('Features Section', {
            'fields': ('features_title', 'features_subtitle')
        }),
        ('Process Section', {
            'fields': (
                'process_title',
                'process_step_1_title',
                'process_step_1_description',
                'process_step_2_title',
                'process_step_2_description',
                'process_step_3_title',
                'process_step_3_description',
            )
        }),
        ('Testimonials Section', {
            'fields': ('testimonials_title', 'testimonials_subtitle')
        }),
        ('FAQ Section', {
            'fields': ('faq_title', 'faq_subtitle')
        }),
        ('CTA Section', {
            'fields': (
                'cta_title',
                'cta_subtitle',
                'cta_button_text',
                'cta_disclaimer',
            )
        }),
        ('Floating CTA', {
            'fields': ('floating_cta_text',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not LandingPageSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LandingFeature)
class LandingFeatureAdmin(admin.ModelAdmin):
    """Admin for landing page features."""
    list_display = ['title', 'icon', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'icon']
    search_fields = ['title', 'description']
    ordering = ['order']


@admin.register(LandingStat)
class LandingStatAdmin(admin.ModelAdmin):
    """Admin for landing page statistics."""
    list_display = ['value', 'label', 'order', 'is_animated', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'is_animated']
    ordering = ['order']


@admin.register(LandingTestimonial)
class LandingTestimonialAdmin(admin.ModelAdmin):
    """Admin for landing page testimonials."""
    list_display = ['author_name', 'author_title', 'rating', 'order', 'is_active']
    list_editable = ['order', 'is_active', 'rating']
    list_filter = ['is_active', 'rating']
    search_fields = ['author_name', 'author_title', 'quote']
    ordering = ['order']


@admin.register(LandingFAQ)
class LandingFAQAdmin(admin.ModelAdmin):
    """Admin for landing page FAQs."""
    list_display = ['question', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['question', 'answer']
    ordering = ['order']


@admin.register(LandingTrustedCompany)
class LandingTrustedCompanyAdmin(admin.ModelAdmin):
    """Admin for trusted companies logos."""
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['order']


@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    """Admin for user-submitted reviews with moderation."""
    list_display = ['user', 'rating', 'status', 'created_at', 'reviewed_by']
    list_filter = ['status', 'rating', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'quote']
    readonly_fields = ['user', 'quote', 'rating', 'created_at', 'updated_at']
    ordering = ['-created_at']
    actions = ['approve_reviews', 'reject_reviews']
    
    fieldsets = (
        ('Review Content', {
            'fields': ('user', 'quote', 'rating', 'created_at')
        }),
        ('Display Settings', {
            'fields': ('display_name', 'display_title')
        }),
        ('Moderation', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason')
        }),
    )
    
    def approve_reviews(self, request, queryset):
        """Bulk approve selected reviews."""
        count = 0
        for review in queryset.filter(status='pending'):
            review.approve(request.user)
            count += 1
        self.message_user(request, f'{count} review(s) approved.')
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        """Bulk reject selected reviews."""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{count} review(s) rejected.')
    reject_reviews.short_description = "Reject selected reviews"
