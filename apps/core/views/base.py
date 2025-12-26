"""
Base Views - Common functionality for all view classes.

Provides:
- Standardized authentication/authorization
- Common context data
- Error handling
- Audit logging for sensitive views
- JSON response helpers
"""
from django.views.generic import (
    View, TemplateView, ListView, DetailView,
    CreateView, UpdateView, DeleteView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


class BaseContextMixin:
    """
    Mixin to add common context data to all views.
    """
    
    # Override in subclass for page title
    page_title = None
    
    # Override for breadcrumbs [(label, url), ...]
    breadcrumbs = []
    
    def get_context_data(self, **kwargs):
        """Get common context data. Safely calls super() if it exists."""
        if hasattr(super(), 'get_context_data'):
            context = super().get_context_data(**kwargs)
        else:
            context = kwargs.copy()
        
        # Page metadata
        context['page_title'] = self.get_page_title()
        context['breadcrumbs'] = self.get_breadcrumbs()
        
        # User info
        if self.request.user and self.request.user.is_authenticated:
            context['current_user'] = self.request.user
            context['user_type'] = getattr(self.request.user, 'user_type', None)
        
        return context
    
    def get_service(self, service_class):
        """Get a service instance initialized with the current user."""
        return service_class(user=self.request.user if self.request.user.is_authenticated else None)
    
    def get_page_title(self):
        """Get page title. Override for dynamic titles."""
        return self.page_title or self.__class__.__name__.replace('View', '')
    
    def get_breadcrumbs(self):
        """Get breadcrumbs. Override for dynamic breadcrumbs."""
        return self.breadcrumbs


class MessageMixin:
    """Mixin for adding success/error messages."""
    
    success_message = ''
    error_message = ''
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.get_success_message())
        return response
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.error_message:
            messages.error(self.request, self.get_error_message())
        return response
    
    def get_success_message(self):
        """Override to customize success message."""
        return self.success_message
    
    def get_error_message(self):
        """Override to customize error message."""
        return self.error_message


class AuditMixin:
    """Mixin for audit logging sensitive view access."""
    
    # Override to enable audit logging
    audit_view_access = False
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if self.audit_view_access and request.user.is_authenticated:
            self._log_view_access(request)
        
        return response
    
    def _log_view_access(self, request):
        """Log view access to audit log."""
        try:
            from apps.core.models import AuditLog
            
            AuditLog.log_action(
                user=request.user,
                action='VIEW',
                changes={
                    'view': self.__class__.__name__,
                    'path': request.path,
                    'method': request.method,
                }
            )
        except Exception as e:
            logger.warning(f'Failed to log view access: {e}')


class JsonResponseMixin:
    """Mixin for JSON response helpers."""
    
    def json_response(self, data, status=200):
        """Return JSON response with data."""
        return JsonResponse(data, status=status, safe=False)
    
    def json_success(self, message='Success', data=None):
        """Return success JSON response."""
        response = {'success': True, 'message': message}
        if data:
            response['data'] = data
        return self.json_response(response)
    
    def json_error(self, message='Error', errors=None, status=400):
        """Return error JSON response."""
        response = {'success': False, 'message': message}
        if errors:
            response['errors'] = errors
        return self.json_response(response, status=status)
    
    def json_not_found(self, message='Not found'):
        """Return 404 JSON response."""
        return self.json_error(message, status=404)
    
    def json_forbidden(self, message='Permission denied'):
        """Return 403 JSON response."""
        return self.json_error(message, status=403)


class OwnerRequiredMixin:
    """
    Mixin that ensures only the owner can access the object.
    """
    
    owner_field = 'user'  # Override to change owner field name
    
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(**{self.owner_field: self.request.user})


class CustomerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require user to be a customer."""
    
    def test_func(self):
        return self.request.user.is_authenticated and (
            getattr(self.request.user, 'is_customer', False) or self.request.user.is_superuser
        )
    
    def handle_no_permission(self):
        messages.error(self.request, 'Access denied. Customer account required.')
        return redirect('dashboard:home')


class AgentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require user to be an agent."""
    
    def test_func(self):
        return self.request.user.is_authenticated and (
            getattr(self.request.user, 'is_agent', False) or self.request.user.is_superuser
        )
    
    def handle_no_permission(self):
        messages.error(self.request, 'Access denied. Agent account required.')
        return redirect('dashboard:home')


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require user to be staff."""
    
    def test_func(self):
        return self.request.user.is_authenticated and (
            getattr(self.request.user, 'is_staff_member', False) or 
            getattr(self.request.user, 'is_agent', False) or 
            self.request.user.is_superuser
        )
    
    def handle_no_permission(self):
        messages.error(self.request, 'Access denied. Staff access required.')
        return redirect('dashboard:home')


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require user to be admin."""
    
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or getattr(self.request.user, 'is_admin', False)
        )
    
    def handle_no_permission(self):
        messages.error(self.request, 'Administrator access required.')
        return redirect('dashboard:home')


# ==================== Base View Classes ====================


class BaseView(BaseContextMixin, View):
    """Base view with common context."""
    pass


class BaseTemplateView(BaseContextMixin, TemplateView):
    """Base template view with common context."""
    pass


class BaseListView(BaseContextMixin, ListView):
    """
    Base list view with pagination and search.
    """
    
    paginate_by = 20
    search_fields = []  # Fields to search in
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Handle search
        search_query = self.request.GET.get('q', '').strip()
        if search_query and self.search_fields:
            from django.db.models import Q
            q = Q()
            for field in self.search_fields:
                q |= Q(**{f'{field}__icontains': search_query})
            qs = qs.filter(q)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class BaseDetailView(BaseContextMixin, AuditMixin, DetailView):
    """Base detail view with audit logging."""
    
    audit_view_access = False  # Enable for sensitive views


class BaseCreateView(BaseContextMixin, MessageMixin, LoginRequiredMixin, CreateView):
    """
    Base create view with user tracking.
    """
    
    success_message = 'Created successfully.'
    
    def form_valid(self, form):
        # Set created_by if model has it
        if hasattr(form.instance, 'created_by'):
            form.instance.created_by = self.request.user
        
        return super().form_valid(form)


class BaseUpdateView(BaseContextMixin, MessageMixin, LoginRequiredMixin, UpdateView):
    """
    Base update view with user tracking.
    """
    
    success_message = 'Updated successfully.'
    
    def form_valid(self, form):
        # Set modified_by if model has it
        if hasattr(form.instance, 'modified_by'):
            form.instance.modified_by = self.request.user
        
        return super().form_valid(form)


class BaseDeleteView(BaseContextMixin, MessageMixin, LoginRequiredMixin, DeleteView):
    """
    Base delete view with soft delete support.
    """
    
    success_message = 'Deleted successfully.'
    soft_delete = True  # Use soft delete if model supports it
    
    def form_valid(self, form):
        obj = self.get_object()
        
        if self.soft_delete and hasattr(obj, 'soft_delete'):
            obj.soft_delete()
            messages.success(self.request, self.success_message)
            return redirect(self.get_success_url())
        elif self.soft_delete and hasattr(obj, 'trash'):
            obj.trash(user=self.request.user)
            messages.success(self.request, self.success_message)
            return redirect(self.get_success_url())
        
        return super().form_valid(form)


class BaseFormView(BaseContextMixin, MessageMixin, LoginRequiredMixin, FormView):
    """Base form view."""
    pass


# ==================== API Views ====================


class BaseAPIView(JsonResponseMixin, View):
    """
    Base view for API endpoints.
    Returns JSON responses.
    """
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            return self.json_not_found()
        except PermissionDenied:
            return self.json_forbidden()
        except Exception as e:
            logger.error(f'API error in {self.__class__.__name__}: {e}')
            return self.json_error('An error occurred', status=500)
    
    def http_method_not_allowed(self, request, *args, **kwargs):
        return self.json_error('Method not allowed', status=405)


class AuthenticatedAPIView(LoginRequiredMixin, BaseAPIView):
    """API view requiring authentication."""
    
    def handle_no_permission(self):
        return self.json_error('Authentication required', status=401)


class StaffAPIView(StaffRequiredMixin, BaseAPIView):
    """API view requiring staff access."""
    
    def handle_no_permission(self):
        return self.json_forbidden('Staff access required')
