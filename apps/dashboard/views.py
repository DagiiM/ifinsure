from django.shortcuts import redirect, render
from django.db.models import Sum, Q
from django.utils import timezone

from apps.core.views.base import (
    BaseView, BaseTemplateView, LoginRequiredMixin,
    StaffRequiredMixin, AdminRequiredMixin
)
from apps.policies.models import Policy, PolicyApplication
from apps.claims.models import Claim
from apps.billing.models import Invoice
from apps.core.landing_models import (
    LandingPageSettings,
    LandingFeature,
    LandingStat,
    LandingTestimonial,
    LandingFAQ,
    LandingTrustedCompany,
    UserReview,
)


class DashboardHomeView(BaseView):
    """Main dashboard - redirects to appropriate role-based dashboard."""
    page_title = 'Welcome to iFin Insurance'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Get dynamic landing page content
            context = self.get_landing_context()
            # Manually add context from BaseContextMixin since we are not using get_context_data
            context.update(self.get_context_data())
            return render(request, 'landing.html', context)
            
        user = request.user
        
        if user.is_admin:
            return redirect('dashboard:admin')
        elif user.is_agent:
            return redirect('dashboard:agent')
        elif user.is_staff_member:
            return redirect('dashboard:staff')
        else:
            return redirect('dashboard:customer')
    
    def get_landing_context(self):
        """Get context data for the landing page."""
        from apps.policies.models import InsuranceProduct
        
        # Get settings (creates default if not exists)
        settings = LandingPageSettings.get_settings()
        
        # Get active content
        features = LandingFeature.objects.filter(is_active=True)
        stats = LandingStat.objects.filter(is_active=True)
        
        # Get testimonials - combine admin-created and approved user reviews
        admin_testimonials = LandingTestimonial.objects.filter(is_active=True)
        user_reviews = UserReview.objects.filter(status='approved', is_active=True)[:6]
        
        faqs = LandingFAQ.objects.filter(is_active=True)
        trusted_companies = LandingTrustedCompany.objects.filter(is_active=True)
        
        # Get insurance products for marketplace section
        products = InsuranceProduct.objects.filter(is_active=True)[:6]
        
        return {
            'settings': settings,
            'features': features,
            'stats': stats,
            'testimonials': admin_testimonials,
            'user_reviews': user_reviews,
            'faqs': faqs,
            'trusted_companies': trusted_companies,
            'products': products,
        }


class CustomerDashboardView(LoginRequiredMixin, BaseTemplateView):
    """Customer dashboard with policy and claim overview."""
    template_name = 'dashboard/customer.html'
    page_title = 'Customer Dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Active policies
        policies = Policy.objects.filter(
            customer=user,
            is_active=True
        ).select_related('product')
        
        context['active_policies'] = policies.filter(status='active')[:5]
        context['policy_count'] = policies.filter(status='active').count()
        context['expiring_soon'] = policies.filter(
            status='active',
            end_date__lte=timezone.now().date() + timezone.timedelta(days=30),
            end_date__gte=timezone.now().date()
        ).count()
        
        # Claims
        claims = Claim.objects.filter(
            claimant=user,
            is_active=True
        )
        context['recent_claims'] = claims.order_by('-created_at')[:5]
        context['pending_claims'] = claims.filter(
            status__in=['submitted', 'under_review', 'investigating']
        ).count()
        
        # Invoices
        invoices = Invoice.objects.filter(
            customer=user,
            is_active=True
        )
        context['pending_invoices'] = invoices.filter(
            status__in=['pending', 'partial', 'overdue']
        )[:5]
        context['total_due'] = invoices.filter(
            status__in=['pending', 'partial', 'overdue']
        ).aggregate(
            total=Sum('amount') - Sum('paid_amount')
        )['total'] or 0
        context['overdue_count'] = invoices.filter(status='overdue').count()
        
        # Total coverage
        context['total_coverage'] = policies.filter(
            status='active'
        ).aggregate(total=Sum('coverage_amount'))['total'] or 0
        
        return context


class AgentDashboardView(LoginRequiredMixin, BaseTemplateView):
    """Agent dashboard with portfolio overview."""
    template_name = 'dashboard/agent.html'
    page_title = 'Agent Dashboard'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_agent or request.user.is_superuser):
            return redirect('dashboard:customer')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Managed policies
        if user.is_superuser:
            policies = Policy.objects.filter(is_active=True)
            applications = PolicyApplication.objects.filter(is_active=True)
            claims = Claim.objects.filter(is_active=True)
        else:
            policies = Policy.objects.filter(agent=user, is_active=True)
            applications = PolicyApplication.objects.filter(
                Q(assigned_agent=user) | Q(assigned_agent__isnull=True),
                is_active=True
            )
            claims = Claim.objects.filter(
                Q(assigned_adjuster=user) | Q(assigned_adjuster__isnull=True),
                is_active=True
            )
        
        # Policy stats
        context['total_policies'] = policies.filter(status='active').count()
        context['policies_value'] = policies.filter(
            status='active'
        ).aggregate(total=Sum('premium_amount'))['total'] or 0
        
        # Pending applications
        context['pending_applications'] = applications.filter(
            status__in=['submitted', 'under_review']
        ).order_by('-created_at')[:10]
        context['pending_app_count'] = context['pending_applications'].count()
        
        # Claims requiring attention
        context['pending_claims'] = claims.filter(
            status__in=['submitted', 'under_review', 'investigating']
        ).order_by('-created_at')[:10]
        context['pending_claim_count'] = context['pending_claims'].count()
        
        # Recent policies
        context['recent_policies'] = policies.order_by('-created_at')[:5]
        
        # Expiring policies
        context['expiring_policies'] = policies.filter(
            status='active',
            end_date__lte=timezone.now().date() + timezone.timedelta(days=30),
            end_date__gte=timezone.now().date()
        ).count()
        
        return context


class StaffDashboardView(StaffRequiredMixin, BaseTemplateView):
    """Staff dashboard focused on processing tasks."""
    template_name = 'dashboard/staff.html'
    page_title = 'Staff Dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Claims to process
        claims = Claim.objects.filter(is_active=True)
        context['claims_to_review'] = claims.filter(
            status__in=['submitted', 'under_review']
        ).count()
        context['investigating_claims'] = claims.filter(status='investigating').count()
        context['approved_claims'] = claims.filter(
            status__in=['approved', 'partially_approved']
        ).count()
        
        # Recent claims
        context['recent_claims'] = claims.filter(
            status__in=['submitted', 'under_review', 'investigating']
        ).order_by('-created_at')[:10]
        
        # Billing
        invoices = Invoice.objects.filter(is_active=True)
        context['overdue_invoices'] = invoices.filter(status='overdue').count()
        context['pending_payments'] = invoices.filter(
            status__in=['pending', 'partial']
        ).aggregate(total=Sum('amount') - Sum('paid_amount'))['total'] or 0
        
        return context


class AdminDashboardView(AdminRequiredMixin, BaseTemplateView):
    """Admin dashboard with system-wide overview."""
    template_name = 'dashboard/admin.html'
    page_title = 'System Overview'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounts.models import User
        
        # User stats
        context['total_users'] = User.objects.filter(is_active=True).count()
        context['customers'] = User.objects.filter(user_type='customer', is_active=True).count()
        context['agents'] = User.objects.filter(user_type='agent', is_active=True).count()
        context['staff'] = User.objects.filter(user_type='staff', is_active=True).count()
        
        # Policy stats
        policies = Policy.objects.filter(is_active=True)
        context['total_policies'] = policies.filter(status='active').count()
        context['total_coverage'] = policies.filter(
            status='active'
        ).aggregate(total=Sum('coverage_amount'))['total'] or 0
        context['monthly_premiums'] = policies.filter(
            status='active'
        ).aggregate(total=Sum('premium_amount'))['total'] or 0
        
        # Claims stats
        claims = Claim.objects.filter(is_active=True)
        context['total_claims'] = claims.count()
        context['pending_claims'] = claims.filter(
            status__in=['submitted', 'under_review', 'investigating']
        ).count()
        context['claims_value'] = claims.filter(
            status__in=['approved', 'partially_approved', 'paid']
        ).aggregate(total=Sum('approved_amount'))['total'] or 0
        
        # Billing stats
        invoices = Invoice.objects.filter(is_active=True)
        context['total_invoiced'] = invoices.aggregate(total=Sum('amount'))['total'] or 0
        context['total_collected'] = invoices.aggregate(total=Sum('paid_amount'))['total'] or 0
        context['overdue_amount'] = invoices.filter(status='overdue').aggregate(
            total=Sum('amount') - Sum('paid_amount')
        )['total'] or 0
        
        # Recent activity
        context['recent_policies'] = policies.order_by('-created_at')[:5]
        context['recent_claims'] = claims.order_by('-created_at')[:5]
        
        # Applications needing review
        context['pending_applications'] = PolicyApplication.objects.filter(
            status__in=['submitted', 'under_review'],
            is_active=True
        ).count()
        
        return context
