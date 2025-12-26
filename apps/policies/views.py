"""
Policies views.
"""
from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.contrib import messages

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseDetailView, BaseCreateView, BaseUpdateView,
    LoginRequiredMixin
)
from apps.core.mixins import CustomerRequiredMixin, AgentRequiredMixin
from .models import Policy, PolicyApplication, InsuranceProduct
from .forms import PolicyApplicationForm, ApplicationReviewForm, PolicyFilterForm
from .services import PolicyService, ApplicationPaymentService
from .cart import get_cart


# ============================================
# PUBLIC VIEWS (No Login Required)
# ============================================

class PublicProductListView(BaseListView):
    """
    Public products page - works for anonymous users.
    Displays all available insurance products in a marketplace style.
    """
    model = InsuranceProduct
    template_name = 'policies/public_products.html'
    context_object_name = 'products'
    page_title = 'Insurance Marketplace'
    
    def get_queryset(self):
        qs = InsuranceProduct.objects.filter(is_active=True)
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category__code=category)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(code__icontains=search)
            )
        
        # Sort
        sort = self.request.GET.get('sort', 'name')
        if sort == 'price_low':
            qs = qs.order_by('base_premium')
        elif sort == 'price_high':
            qs = qs.order_by('-base_premium')
        elif sort == 'name':
            qs = qs.order_by('name')
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = InsuranceProduct.CATEGORY_CHOICES
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['sort'] = self.request.GET.get('sort', 'name')
        cart = get_cart(self.request)
        context['cart'] = cart
        # Pre-compute which product IDs are in cart for template use
        context['cart_product_ids'] = [pk for pk in cart.cart.keys()]
        return context


class PublicProductDetailView(BaseDetailView):
    """
    Public product detail page - works for anonymous users.
    Shows full product details and allows adding to cart.
    """
    model = InsuranceProduct
    template_name = 'policies/public_product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return InsuranceProduct.objects.filter(is_active=True)
    
    def get_page_title(self):
        return f"Product: {self.object.name}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = get_cart(self.request)
        context['in_cart'] = context['cart'].has_product(self.object.pk)
        context['related_products'] = InsuranceProduct.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(pk=self.object.pk)[:3]
        return context


# ============================================
# CART VIEWS (Anonymous + Authenticated)
# ============================================

class CartView(BaseTemplateView):
    """View the shopping cart."""
    template_name = 'policies/cart.html'
    page_title = 'Your Cart'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = get_cart(self.request)
        return context


class CartAddView(BaseView):
    """Add a product to the cart."""
    
    def post(self, request, pk):
        product = get_object_or_404(InsuranceProduct, pk=pk, is_active=True)
        cart = get_cart(request)
        
        # Get coverage amount from form (default to min_coverage)
        try:
            coverage = Decimal(request.POST.get('coverage_amount', str(product.min_coverage)))
            # Validate coverage within bounds
            coverage = max(coverage, product.min_coverage)
            coverage = min(coverage, product.max_coverage)
        except (InvalidOperation, TypeError):
            coverage = product.min_coverage
        
        term_months = int(request.POST.get('term_months', 12))
        payment_frequency = request.POST.get('payment_frequency', 'monthly')
        
        cart.add(product, coverage, term_months, payment_frequency)
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'{product.name} added to cart',
                'cart_count': len(cart),
                'cart_total': str(cart.get_total_premium()),
            })
        
        messages.success(request, f'{product.name} added to your cart!')
        
        # Redirect back or to cart
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', reverse('policies:cart')))
        return redirect(next_url)


class CartUpdateView(BaseView):
    """Update a cart item."""
    
    def post(self, request, pk):
        cart = get_cart(request)
        
        try:
            coverage = request.POST.get('coverage_amount')
            if coverage:
                coverage = Decimal(coverage)
            else:
                coverage = None
        except (InvalidOperation, TypeError):
            coverage = None
        
        term_months = request.POST.get('term_months')
        if term_months:
            term_months = int(term_months)
        else:
            term_months = None
        
        payment_frequency = request.POST.get('payment_frequency')
        
        cart.update(pk, coverage, term_months, payment_frequency)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'cart_total': str(cart.get_total_premium()),
            })
        
        messages.success(request, 'Cart updated!')
        return redirect('policies:cart')


class CartRemoveView(BaseView):
    """Remove a product from the cart."""
    
    def post(self, request, pk):
        cart = get_cart(request)
        item = cart.get_item(pk)
        product_name = item['product_name'] if item else 'Product'
        cart.remove(pk)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'{product_name} removed from cart',
                'cart_count': len(cart),
                'cart_total': str(cart.get_total_premium()),
            })
        
        messages.success(request, f'{product_name} removed from your cart.')
        return redirect('policies:cart')


class CartClearView(BaseView):
    """Clear all items from the cart."""
    
    def post(self, request):
        cart = get_cart(request)
        cart.clear()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Cart cleared',
                'cart_count': 0,
                'cart_total': '0',
            })
        
        messages.success(request, 'Your cart has been cleared.')
        return redirect('policies:cart')


class CartCheckoutView(BaseView):
    """
    Checkout process - requires login.
    Converts cart items to policy applications.
    """
    
    def get(self, request):
        cart = get_cart(request)
        
        if cart.is_empty():
            messages.warning(request, 'Your cart is empty.')
            return redirect('policies:public_products')
        
        if not request.user.is_authenticated:
            # Store cart and redirect to login
            messages.info(request, 'Please log in or register to complete your application.')
            return redirect(f"{reverse('accounts:login')}?next={reverse('policies:checkout')}")
        
        # Show checkout page
        return redirect('policies:apply_from_cart')


class ApplyFromCartView(CustomerRequiredMixin, BaseTemplateView):
    """Create applications from cart items."""
    template_name = 'policies/apply_from_cart.html'
    page_title = 'Complete Application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = get_cart(self.request)
        return context
    
    def post(self, request):
        cart = get_cart(request)
        
        if cart.is_empty():
            messages.warning(request, 'Your cart is empty.')
            return redirect('policies:public_products')
        
        # Create applications for each cart item
        created = 0
        for item in cart:
            product = item.get('product')
            if product:
                application = PolicyApplication.objects.create(
                    applicant=request.user,
                    product=product,
                    requested_coverage=item['coverage_amount'],
                    requested_term_months=item['term_months'],
                    payment_frequency=item['payment_frequency'],
                    calculated_premium=item['premium'],
                    status='draft',
                )
                created += 1
        
        # Clear the cart
        cart.clear()
        
        messages.success(
            request, 
            f'{created} application(s) created! Review and submit them to complete your purchase.'
        )
        return redirect('policies:applications')


# ============================================
# CUSTOMER VIEWS (Login Required)
# ============================================

class PolicyListView(CustomerRequiredMixin, BaseListView):
    """List policies for the current customer."""
    model = Policy
    template_name = 'policies/list.html'
    context_object_name = 'policies'
    page_title = 'My Policies'
    
    def get_queryset(self):
        qs = super().get_queryset().filter(
            customer=self.request.user,
            is_active=True
        ).select_related('product')
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PolicyFilterForm(self.request.GET)
        context['status_counts'] = {
            'active': self.get_queryset().filter(status='active').count(),
            'pending': self.get_queryset().filter(status='pending').count(),
            'expired': self.get_queryset().filter(status='expired').count(),
        }
        return context


class PolicyDetailView(BaseDetailView):
    """View policy details. Customers can only see their own, staff can see all."""
    model = Policy
    template_name = 'policies/detail.html'
    context_object_name = 'policy'
    
    def get_queryset(self):
        qs = Policy.objects.select_related('product', 'agent', 'customer')
        
        # Staff and agents can view all policies
        if self.request.user.is_staff or getattr(self.request.user, 'user_type', '') == 'agent':
            return qs
        
        # Customers can only view their own policies
        return qs.filter(customer=self.request.user)
    
    def get_page_title(self):
        return f"Policy: {self.object.policy_number}"


class ProductListView(BaseListView):
    """List available insurance products."""
    model = InsuranceProduct
    template_name = 'policies/products.html'
    context_object_name = 'products'
    page_title = 'Insurance Products'
    
    def get_queryset(self):
        qs = InsuranceProduct.objects.filter(is_active=True)
        
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category__code=category)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = InsuranceProduct.CATEGORY_CHOICES
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class ProductDetailView(BaseDetailView):
    """View product details."""
    model = InsuranceProduct
    template_name = 'policies/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return InsuranceProduct.objects.filter(is_active=True)
    
    def get_page_title(self):
        return f"Product: {self.object.name}"


class ApplicationCreateView(CustomerRequiredMixin, BaseCreateView):
    """Create new policy application."""
    model = PolicyApplication
    form_class = PolicyApplicationForm
    template_name = 'policies/apply.html'
    success_url = reverse_lazy('policies:applications')
    success_message = 'Application created successfully. Submit it when ready.'
    page_title = 'Apply for Policy'
    
    def get_initial(self):
        initial = super().get_initial()
        product_id = self.request.GET.get('product')
        if product_id:
            initial['product'] = product_id
        return initial
    
    def form_valid(self, form):
        form.instance.applicant = self.request.user
        form.instance.status = 'draft'
        return super().form_valid(form)


class ApplicationListView(CustomerRequiredMixin, BaseListView):
    """List applications for the current customer."""
    model = PolicyApplication
    template_name = 'policies/applications.html'
    context_object_name = 'applications'
    page_title = 'My Applications'
    
    def get_queryset(self):
        return PolicyApplication.objects.filter(
            applicant=self.request.user,
            is_active=True
        ).select_related('product').order_by('-created_at')


class ApplicationDetailView(CustomerRequiredMixin, BaseDetailView):
    """View application details."""
    model = PolicyApplication
    template_name = 'policies/application_detail.html'
    context_object_name = 'application'
    
    def get_queryset(self):
        return PolicyApplication.objects.filter(
            applicant=self.request.user
        ).select_related('product', 'assigned_agent', 'reviewed_by')
    
    def get_page_title(self):
        return f"Application: {self.object.application_number}"
    
    def post(self, request, *args, **kwargs):
        """Handle application submission."""
        application = self.get_object()
        policy_service = self.get_service(PolicyService)
        
        if 'submit' in request.POST and application.status == 'draft':
            try:
                policy_service.submit_application(application)
                messages.success(request, 'Application submitted successfully!')
            except ValueError as e:
                messages.error(request, str(e))
        
        return redirect('policies:application_detail', pk=application.pk)


# Agent/Staff Views
class AgentPolicyListView(AgentRequiredMixin, BaseListView):
    """List policies for agent's portfolio."""
    model = Policy
    template_name = 'policies/agent/policy_list.html'
    context_object_name = 'policies'
    page_title = 'Policy Portfolio'
    search_fields = ['policy_number', 'customer__email', 'customer__first_name', 'customer__last_name']
    
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        
        if not self.request.user.is_superuser:
            qs = qs.filter(agent=self.request.user)
        
        # Search/filter
        # The search logic is now handled by BaseListView's get_queryset if search_fields is defined.
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        return qs.select_related('customer', 'product')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PolicyFilterForm(self.request.GET)
        return context


class AgentApplicationListView(AgentRequiredMixin, BaseListView):
    """List applications for agent review."""
    model = PolicyApplication
    template_name = 'policies/agent/application_list.html'
    context_object_name = 'applications'
    page_title = 'Application Queue'
    
    def get_queryset(self):
        qs = super().get_queryset().filter(
            is_active=True,
            status__in=['submitted', 'under_review']
        )
        
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(assigned_agent=self.request.user) |
                Q(assigned_agent__isnull=True)
            )
        
        return qs.select_related('applicant', 'product')


class AgentApplicationReviewView(AgentRequiredMixin, BaseDetailView):
    """Review and process application."""
    model = PolicyApplication
    template_name = 'policies/agent/application_review.html'
    context_object_name = 'application'
    
    def get_queryset(self):
        return PolicyApplication.objects.filter(
            is_active=True
        ).select_related('applicant', 'product')
    
    def get_page_title(self):
        return f"Review: {self.object.application_number}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['review_form'] = ApplicationReviewForm()
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        application = self.object
        form = ApplicationReviewForm(request.POST)
        policy_service = self.get_service(PolicyService)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data['notes']
            
            try:
                if action == 'approve':
                    policy = policy_service.approve_application(
                        application, notes
                    )
                    messages.success(
                        request,
                        f'Application approved! Policy {policy.policy_number} created.'
                    )
                else:
                    policy_service.reject_application(
                        application, notes
                    )
                    messages.success(request, 'Application rejected.')
                
                return redirect('policies:agent_applications')
            except PermissionError as e:
                messages.error(request, str(e))
            except ValueError as e:
                messages.error(request, str(e))
        
        context = self.get_context_data()
        context['review_form'] = form
        return self.render_to_response(context)


