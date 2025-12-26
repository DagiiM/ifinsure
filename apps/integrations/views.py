import json
from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.db.models import Avg

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseDetailView, BaseCreateView, BaseUpdateView,
    AdminRequiredMixin
)
from .models import (
    IntegrationCategory, IntegrationProvider, 
    IntegrationConfig, IntegrationLog, WebhookEvent
)
from .forms import IntegrationConfigForm, IntegrationFilterForm
from .services import IntegrationService


class IntegrationsDashboardView(AdminRequiredMixin, BaseListView):
    """Main integrations center dashboard"""
    model = IntegrationCategory
    template_name = 'integrations/dashboard.html'
    context_object_name = 'categories'
    page_title = 'Integrations Center'
    
    def get_queryset(self):
        return IntegrationCategory.objects.filter(is_active=True).order_by('display_order')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['active_integrations'] = IntegrationConfig.objects.filter(
            is_enabled=True
        ).count()
        
        context['total_providers'] = IntegrationProvider.objects.filter(
            is_available=True
        ).count()
        
        # Configs needing attention (failed tests, etc.)
        context['needs_attention'] = IntegrationConfig.objects.filter(
            is_enabled=True,
            last_test_status='failed'
        ).count()
        
        # API calls today
        today = timezone.now().replace(hour=0, minute=0, second=0)
        context['api_calls_today'] = IntegrationLog.objects.filter(
            created_at__gte=today
        ).count()
        
        # Recent logs
        context['recent_logs'] = IntegrationLog.objects.select_related(
            'config', 'config__provider'
        ).order_by('-created_at')[:10]
        
        return context


class CategoryDetailView(AdminRequiredMixin, BaseDetailView):
    """View providers in a category"""
    model = IntegrationCategory
    template_name = 'integrations/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_page_title(self):
        return f"Category: {self.object.name}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all providers for this category
        providers = IntegrationProvider.objects.filter(
            category=self.object,
            is_available=True
        )
        
        # Check which have configs
        for provider in providers:
            config = IntegrationConfig.objects.filter(provider=provider).first()
            if config:
                provider.config_exists = True
                provider.config_pk = config.pk
            else:
                provider.config_exists = False
        
        context['providers'] = providers
        
        # Get active configs
        context['configs'] = IntegrationConfig.objects.filter(
            provider__category=self.object
        ).select_related('provider')
        
        return context


class ProviderDetailView(AdminRequiredMixin, BaseDetailView):
    """View provider information"""
    model = IntegrationProvider
    template_name = 'integrations/provider_detail.html'
    context_object_name = 'provider'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_page_title(self):
        return f"Provider: {self.object.name}"


class ConfigureProviderView(AdminRequiredMixin, BaseCreateView):
    """Configure a new integration"""
    model = IntegrationConfig
    form_class = IntegrationConfigForm
    template_name = 'integrations/configure.html'
    page_title = 'Configure Integration'
    
    def get_provider(self):
        return get_object_or_404(
            IntegrationProvider, 
            slug=self.kwargs['provider_slug'],
            is_available=True
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['provider'] = self.get_provider()
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provider = self.get_provider()
        context['provider'] = provider
        
        # Generate webhook URL
        context['webhook_url'] = self.request.build_absolute_uri(
            reverse('integrations:webhook', kwargs={'provider': provider.slug})
        )
        
        return context
    
    def form_valid(self, form):
        form.instance.provider = self.get_provider()
        messages.success(self.request, f'Successfully configured {form.instance.provider.name}')
        
        # Test connection if requested
        if 'test_connection' in self.request.POST:
            instance = form.save()
            integration_service = self.get_service(IntegrationService)
            if integration_service.test_connection(instance):
                messages.success(self.request, 'Connection test successful!')
            else:
                messages.warning(self.request, f'Connection test failed: {instance.last_test_message}')
            return redirect('integrations:config_detail', pk=instance.pk)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('integrations:config_detail', kwargs={'pk': self.object.pk})


class ConfigDetailView(AdminRequiredMixin, BaseDetailView):
    """View integration configuration details"""
    model = IntegrationConfig
    template_name = 'integrations/config_detail.html'
    context_object_name = 'config'
    
    def get_page_title(self):
        return f"Configuration: {self.object.name}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Generate webhook URL
        context['webhook_url'] = self.request.build_absolute_uri(
            reverse('integrations:webhook', kwargs={'provider': self.object.provider.slug})
        )
        
        # Recent logs for this config
        context['recent_logs'] = IntegrationLog.objects.filter(
            config=self.object
        ).order_by('-created_at')[:20]
        
        # Usage statistics
        integration_service = self.get_service(IntegrationService)
        context['stats'] = integration_service.get_config_stats(self.object)
        
        return context


class ConfigUpdateView(AdminRequiredMixin, BaseUpdateView):
    """Edit integration configuration"""
    model = IntegrationConfig
    form_class = IntegrationConfigForm
    template_name = 'integrations/configure.html'
    page_title = 'Update Configuration'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['provider'] = self.object.provider
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['provider'] = self.object.provider
        context['webhook_url'] = self.request.build_absolute_uri(
            reverse('integrations:webhook', kwargs={'provider': self.object.provider.slug})
        )
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Configuration updated successfully')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('integrations:config_detail', kwargs={'pk': self.object.pk})


class ToggleConfigView(AdminRequiredMixin, BaseView):
    """Toggle integration enabled/disabled"""
    
    def post(self, request, pk):
        config = get_object_or_404(IntegrationConfig, pk=pk)
        integration_service = self.get_service(IntegrationService)
        
        if integration_service.toggle_config(config):
            status = 'enabled' if config.is_enabled else 'disabled'
            messages.success(request, f'{config.name} has been {status}')
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'is_enabled': config.is_enabled,
                    'message': f'{config.name} has been {status}'
                })
        
        return redirect(request.META.get('HTTP_REFERER', 'integrations:dashboard'))


class TestConnectionView(AdminRequiredMixin, BaseView):
    """Test integration connectivity"""
    
    def post(self, request, pk):
        config = get_object_or_404(IntegrationConfig, pk=pk)
        integration_service = self.get_service(IntegrationService)
        success = integration_service.test_connection(config)
        
        return JsonResponse({
            'success': success,
            'message': config.last_test_message,
            'status': config.last_test_status,
            'tested_at': config.last_tested_at.isoformat() if config.last_tested_at else None
        })


class IntegrationLogsView(AdminRequiredMixin, BaseListView):
    """View integration activity logs"""
    model = IntegrationLog
    template_name = 'integrations/logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    page_title = 'Integration Logs'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'config', 'config__provider'
        ).order_by('-created_at')
        
        # Apply filters
        provider_id = self.request.GET.get('provider')
        if provider_id:
            queryset = queryset.filter(config__provider_id=provider_id)
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        date_range = self.request.GET.get('date_range', 'week')
        today = timezone.now().replace(hour=0, minute=0, second=0)
        
        if date_range == 'today':
            queryset = queryset.filter(created_at__gte=today)
        elif date_range == 'week':
            queryset = queryset.filter(created_at__gte=today - timedelta(days=7))
        elif date_range == 'month':
            queryset = queryset.filter(created_at__gte=today - timedelta(days=30))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = IntegrationFilterForm(self.request.GET)
        context['providers'] = IntegrationProvider.objects.filter(is_available=True)
        
        # Stats for filtered period
        queryset = self.get_queryset()
        context['stats'] = {
            'total': queryset.count(),
            'success': queryset.filter(status='success').count(),
            'failed': queryset.filter(status='failed').count(),
            'avg_response': queryset.aggregate(
                avg=Avg('response_time_ms')
            )['avg'] or 0
        }
        
        return context


class LogDetailView(AdminRequiredMixin, BaseView):
    """Get log details (AJAX)"""
    
    def get(self, request, pk):
        log = get_object_or_404(IntegrationLog, pk=pk)
        return JsonResponse({
            'id': log.pk,
            'action': log.action,
            'status': log.status,
            'request_data': log.request_data,
            'response_data': log.response_data,
            'error_message': log.error_message,
            'response_time_ms': log.response_time_ms,
            'created_at': log.created_at.isoformat()
        })


class WebhookView(BaseView):
    """Handle incoming webhooks from providers"""
    
    def post(self, request, provider):
        # Get provider
        provider_obj = get_object_or_404(IntegrationProvider, slug=provider)
        
        # Find active config
        config = IntegrationConfig.objects.filter(
            provider=provider_obj,
            is_enabled=True
        ).first()
        
        if not config:
            return JsonResponse({'error': 'No active configuration'}, status=400)
        
        # Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            payload = {}
        
        integration_service = self.get_service(IntegrationService)
        result = integration_service.handle_webhook(config, payload, dict(request.headers), request.META.get('REMOTE_ADDR'))
        
        if result:
            return JsonResponse({'status': 'received'})
        return JsonResponse({'status': 'failed'}, status=500)
    
    def get(self, request, provider):
        # Some providers send GET requests for verification
        return JsonResponse({'status': 'ok'})
