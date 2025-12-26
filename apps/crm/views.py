from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseDetailView, BaseCreateView, BaseUpdateView
)
from apps.core.mixins import StaffRequiredMixin
from apps.crm.models import (
    InsuranceProvider, ProductCategory, InsuranceProduct,
    Customer, Lead
)
from .services import CRMService


# ============ PROVIDER VIEWS ============

class ProviderListView(StaffRequiredMixin, BaseListView):
    """List all insurance providers."""
    model = InsuranceProvider
    template_name = 'crm/provider_list.html'
    context_object_name = 'providers'
    page_title = 'Insurance Providers'
    
    def get_queryset(self):
        return super().get_queryset().annotate(
            product_count=Count('products')
        )


class ProviderDetailView(StaffRequiredMixin, BaseDetailView):
    """View provider details."""
    model = InsuranceProvider
    template_name = 'crm/provider_detail.html'
    context_object_name = 'provider'
    
    def get_page_title(self):
        return f"Provider: {self.object.name}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(is_active=True)
        context['contacts'] = self.object.contacts.all()
        return context


# ============ PRODUCT VIEWS ============

class ProductCatalogView(StaffRequiredMixin, BaseListView):
    """Product catalog with filtering."""
    model = InsuranceProduct
    template_name = 'crm/product_catalog.html'
    context_object_name = 'products'
    page_title = 'Product Catalog'
    search_fields = ['name', 'description', 'provider__name']
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True).select_related('provider', 'category')
        
        # Additional filters
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__code=category)
        
        provider = self.request.GET.get('provider')
        if provider:
            queryset = queryset.filter(provider__code=provider)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ProductCategory.objects.filter(is_active=True)
        context['providers'] = InsuranceProvider.objects.filter(is_active=True)
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_provider'] = self.request.GET.get('provider', '')
        return context


class ProductDetailView(StaffRequiredMixin, BaseDetailView):
    """View product details."""
    model = InsuranceProduct
    template_name = 'crm/product_detail.html'
    context_object_name = 'product'
    slug_field = 'code'
    slug_url_kwarg = 'code'
    
    def get_page_title(self):
        return f"Product: {self.object.name}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = self.object.benefits.all()
        context['related_products'] = InsuranceProduct.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(id=self.object.id)[:4]
        return context


# ============ CUSTOMER VIEWS ============

class CustomerListView(StaffRequiredMixin, BaseListView):
    """List customers with filtering."""
    model = Customer
    template_name = 'crm/customer_list.html'
    context_object_name = 'customers'
    page_title = 'Customers'
    search_fields = ['first_name', 'last_name', 'company_name', 'email', 'phone', 'customer_number']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Additional filters
        customer_type = self.request.GET.get('type')
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        
        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(lifecycle_stage=stage)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_customers'] = Customer.objects.count()
        context['stages'] = Customer.LIFECYCLE_STAGES
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_stage'] = self.request.GET.get('stage', '')
        return context


class CustomerDetailView(StaffRequiredMixin, BaseDetailView):
    """Customer 360° view."""
    model = Customer
    template_name = 'crm/customer_detail.html'
    context_object_name = 'customer'
    
    def get_page_title(self):
        return f"Customer: {self.object.get_full_name()}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['communications'] = self.object.communications.all()[:20]
        context['documents'] = self.object.documents.all()
        
        # Get policies if linked user exists
        if self.object.user:
            from apps.policies.models import Policy
            context['policies'] = Policy.objects.filter(user=self.object.user)[:10]
        
        return context


class CustomerCreateView(StaffRequiredMixin, BaseCreateView):
    """
    Create a new customer.
    Uses CRMService for customer creation with validation and audit logging.
    """
    model = Customer
    template_name = 'crm/customer_form.html'
    page_title = 'New Customer'
    fields = [
        'customer_type', 'first_name', 'middle_name', 'last_name',
        'id_type', 'id_number', 'date_of_birth', 'gender',
        'company_name', 'company_registration', 'kra_pin',
        'email', 'phone', 'alt_phone', 'address', 'city', 'county',
        'source', 'lifecycle_stage', 'notes'
    ]
    
    def form_valid(self, form):
        crm_service = self.get_service(CRMService)
        try:
            # Use CRMService for customer creation
            self.object = crm_service.create_customer(
                customer_type=form.cleaned_data.get('customer_type', 'individual'),
                email=form.cleaned_data.get('email', ''),
                phone=form.cleaned_data.get('phone', ''),
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', ''),
                company_name=form.cleaned_data.get('company_name', ''),
                middle_name=form.cleaned_data.get('middle_name', ''),
                id_type=form.cleaned_data.get('id_type', ''),
                id_number=form.cleaned_data.get('id_number', ''),
                date_of_birth=form.cleaned_data.get('date_of_birth'),
                gender=form.cleaned_data.get('gender', ''),
                kra_pin=form.cleaned_data.get('kra_pin', ''),
                company_registration=form.cleaned_data.get('company_registration', ''),
                alt_phone=form.cleaned_data.get('alt_phone', ''),
                address=form.cleaned_data.get('address', ''),
                city=form.cleaned_data.get('city', ''),
                county=form.cleaned_data.get('county', ''),
                source=form.cleaned_data.get('source', ''),
                lifecycle_stage=form.cleaned_data.get('lifecycle_stage', 'lead'),
                notes=form.cleaned_data.get('notes', '')
            )
            messages.success(self.request, 'Customer created successfully.')
            return redirect(self.get_success_url())
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()


# ============ LEAD VIEWS ============

class LeadListView(StaffRequiredMixin, BaseListView):
    """Lead pipeline view."""
    model = Lead
    template_name = 'crm/lead_list.html'
    context_object_name = 'leads'
    page_title = 'Leads Pipeline'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('interest_category', 'assigned_to')
        
        # Additional filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # My leads only
        if self.request.GET.get('mine'):
            queryset = queryset.filter(assigned_to=self.request.user)
        
        return queryset.order_by('priority', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pipeline counts
        context['pipeline_counts'] = {
            'new': Lead.objects.filter(status='new').count(),
            'contacted': Lead.objects.filter(status='contacted').count(),
            'qualified': Lead.objects.filter(status='qualified').count(),
            'proposal': Lead.objects.filter(status='proposal').count(),
            'won': Lead.objects.filter(status='won').count(),
            'lost': Lead.objects.filter(status='lost').count(),
        }
        
        context['status_choices'] = Lead.STATUS_CHOICES
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class LeadDetailView(StaffRequiredMixin, BaseDetailView):
    """Lead detail view."""
    model = Lead
    template_name = 'crm/lead_detail.html'
    context_object_name = 'lead'
    
    def get_page_title(self):
        return f"Lead: {self.object.get_full_name()}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['communications'] = self.object.communications.all()[:20]
        return context


# ============ CRM DASHBOARD ============

class CRMDashboardView(StaffRequiredMixin, BaseTemplateView):
    """
    CRM homepage/dashboard.
    Uses CRMService for statistics.
    """
    template_name = 'crm/dashboard.html'
    page_title = 'CRM Dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use CRMService for statistics
        crm_service = self.get_service(CRMService)
        stats = crm_service.get_crm_statistics()
        context['customer_count'] = stats['total_customers']
        context['active_customers'] = stats['active_customers']
        context['lead_count'] = stats['total_leads']
        context['conversion_rate'] = stats['conversion_rate']
        context['leads_by_status'] = stats['leads_by_status']
        
        # Additional counts
        context['provider_count'] = InsuranceProvider.objects.filter(is_active=True).count()
        context['product_count'] = InsuranceProduct.objects.filter(is_active=True).count()
        
        # Recent items
        context['recent_customers'] = Customer.objects.order_by('-created_at')[:5]
        context['recent_leads'] = Lead.objects.order_by('-created_at')[:5]
        context['featured_products'] = InsuranceProduct.objects.filter(featured=True, is_active=True)[:6]
        
        # Today's follow-ups
        today = timezone.now().date()
        context['todays_followups'] = Lead.objects.filter(
            follow_up_date=today
        ).select_related('assigned_to')[:10]
        
        return context
