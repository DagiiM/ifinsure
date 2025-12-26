from django.shortcuts import render
from django import forms
from django.urls import reverse_lazy

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseCreateView,
    LoginRequiredMixin
)
from apps.core.landing_models import UserReview


def handler404(request, exception):
    """Custom 404 error handler."""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 error handler."""
    return render(request, 'errors/500.html', status=500)


class UserReviewForm(forms.ModelForm):
    """Form for user review submission."""
    
    class Meta:
        model = UserReview
        fields = ['quote', 'rating', 'display_name', 'display_title']
        widgets = {
            'quote': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share your experience with ifinsure...',
                'class': 'form-control'
            }),
            'rating': forms.Select(choices=[(i, f'{i} Stars') for i in range(5, 0, -1)], attrs={
                'class': 'form-select'
            }),
            'display_name': forms.TextInput(attrs={
                'placeholder': 'Your name (optional)',
                'class': 'form-control'
            }),
            'display_title': forms.TextInput(attrs={
                'placeholder': 'Your title, e.g., CEO, TechCorp (optional)',
                'class': 'form-control'
            }),
        }
        labels = {
            'quote': 'Your Review',
            'rating': 'Rating',
            'display_name': 'Display Name',
            'display_title': 'Your Title',
        }


class SubmitReviewView(BaseCreateView):
    """View for customers to submit reviews."""
    model = UserReview
    form_class = UserReviewForm
    template_name = 'core/submit_review.html'
    success_url = reverse_lazy('core:review_thanks')
    success_message = 'Thank you for your review! It will be published after moderation.'
    page_title = 'Submit a Review'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = 'pending'
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_reviews'] = UserReview.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:5]
        return context


class ReviewThanksView(LoginRequiredMixin, BaseTemplateView):
    """Thank you page after review submission."""
    template_name = 'core/review_thanks.html'
    page_title = 'Thank You'


class MyReviewsView(LoginRequiredMixin, BaseListView):
    """List of user's own reviews."""
    model = UserReview
    template_name = 'core/my_reviews.html'
    context_object_name = 'reviews'
    page_title = 'My Reviews'
    
    def get_queryset(self):
        return UserReview.objects.filter(user=self.request.user).order_by('-created_at')


class SitemapView(BaseTemplateView):
    """Sitemap page showing all available pages."""
    template_name = 'core/sitemap.html'
    page_title = 'Site Map'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pages'] = {
            'Public Pages': [
                {'name': 'Home / Landing Page', 'url': '/', 'description': 'Main landing page'},
                {'name': 'Login', 'url': '/accounts/login/', 'description': 'User authentication'},
                {'name': 'Register', 'url': '/accounts/register/', 'description': 'New account creation'},
            ],
            'Customer Dashboard': [
                {'name': 'Dashboard', 'url': '/customer/', 'description': 'Customer overview'},
                {'name': 'My Policies', 'url': '/policies/', 'description': 'View active policies'},
                {'name': 'My Applications', 'url': '/policies/applications/', 'description': 'Track applications'},
                {'name': 'Apply for Policy', 'url': '/policies/apply/', 'description': 'Start new application'},
                {'name': 'Products', 'url': '/policies/products/', 'description': 'Browse insurance products'},
                {'name': 'My Claims', 'url': '/claims/', 'description': 'View and manage claims'},
                {'name': 'File a Claim', 'url': '/claims/create/', 'description': 'Submit new claim'},
                {'name': 'Billing', 'url': '/billing/', 'description': 'Invoices and payments'},
                {'name': 'Submit Review', 'url': '/review/', 'description': 'Share your experience'},
            ],
            'Account': [
                {'name': 'Profile', 'url': '/accounts/profile/', 'description': 'View profile'},
                {'name': 'Edit Profile', 'url': '/accounts/profile/edit/', 'description': 'Update information'},
                {'name': 'Change Password', 'url': '/accounts/password/change/', 'description': 'Security settings'},
            ],
            'Staff & Admin': [
                {'name': 'Staff Dashboard', 'url': '/staff/', 'description': 'Staff overview'},
                {'name': 'Admin Dashboard', 'url': '/admin/', 'description': 'System administration'},
                {'name': 'Admin Panel', 'url': '/admin/', 'description': 'Django admin'},
            ],
        }
        return context
