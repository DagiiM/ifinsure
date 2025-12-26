---
description: Implementation plan for global resource applications (notifications, search, trash)
---

# Global Resource Applications Implementation Plan

**Project**: ifinsure Insurance Agency Management System  
**Version**: 1.0  
**Date**: December 25, 2024  
**Scope**: Notifications, Search, and Trash Applications

---

## 1. Executive Summary

This implementation plan details the creation of three global resource applications that will enhance the ifinsure system with:
- **Notifications**: Real-time user notifications with multi-channel delivery
- **Search**: Global search across all system models with advanced filtering
- **Trash**: Unified trash management with restoration capabilities

All applications follow the established `apps/accounts` folder structure and leverage existing core mixins (`VisibilityMixin`, `SearchableMixin`, `NotifiableMixin`, `TrashableMixin`).

---

## 2. Folder Structure

Each application mirrors `apps/accounts`:

```
apps/
├── notifications/
│   ├── __init__.py
│   ├── admin/
│   │   ├── __init__.py
│   │   └── admin.py
│   ├── fixtures/
│   ├── forms/
│   │   ├── __init__.py
│   │   └── notification_forms.py
│   ├── migrations/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── notification.py
│   │   └── preferences.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── notification_service.py
│   │   └── delivery_service.py
│   ├── urls.py
│   └── views.py
│
├── search/
│   ├── __init__.py
│   ├── admin/
│   │   ├── __init__.py
│   │   └── admin.py
│   ├── fixtures/
│   ├── forms/
│   │   ├── __init__.py
│   │   └── search_forms.py
│   ├── migrations/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── search_index.py
│   │   └── search_history.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search_service.py
│   │   └── indexer_service.py
│   ├── urls.py
│   └── views.py
│
├── trash/
│   ├── __init__.py
│   ├── admin/
│   │   ├── __init__.py
│   │   └── admin.py
│   ├── fixtures/
│   ├── forms/
│   │   ├── __init__.py
│   │   └── trash_forms.py
│   ├── migrations/
│   ├── models/
│   │   ├── __init__.py
│   │   └── trash_registry.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── trash_service.py
│   ├── urls.py
│   └── views.py
```

---

## 3. Phase 1: Foundation Setup

### 3.1 Create Base Folder Structure

**Duration**: 1 day  
**Priority**: Critical

#### Tasks:
1. Create all three app directories with subdirectories
2. Create `__init__.py` files with AppConfig
3. Register apps in `config/settings/base.py`
4. Add URL includes to `config/urls.py`

#### Files to Create:

**apps/notifications/__init__.py**
```python
"""Notifications app - Real-time user notifications."""
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notifications'
    
    def ready(self):
        from . import signals  # noqa
```

**apps/search/__init__.py**
```python
"""Search app - Global search across all models."""
from django.apps import AppConfig

class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.search'
    verbose_name = 'Global Search'
    
    def ready(self):
        from .services import SearchService
        SearchService.register_all_models()
```

**apps/trash/__init__.py**
```python
"""Trash app - Unified trash management."""
from django.apps import AppConfig

class TrashConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.trash'
    verbose_name = 'Trash Management'
```

### 3.2 Enhanced Visibility Management System

**Duration**: 2 days  
**Priority**: Critical

Extend `apps/core/mixins/visibility.py` with:

```python
# Add to apps/core/mixins/visibility.py

class VisibilityService:
    """
    Centralized visibility management service.
    Controls resource access across all applications.
    """
    
    @staticmethod
    def can_view(user, obj):
        """Check if user can view object."""
        if hasattr(obj, 'is_visible_to'):
            return obj.is_visible_to(user)
        return True
    
    @staticmethod
    def can_edit(user, obj):
        """Check if user can edit object."""
        if hasattr(obj, 'can_edit'):
            return obj.can_edit(user)
        if hasattr(obj, 'owner'):
            return obj.owner == user or user.is_superuser
        return user.is_superuser
    
    @staticmethod
    def can_delete(user, obj):
        """Check if user can delete object."""
        if hasattr(obj, 'can_delete'):
            return obj.can_delete(user)
        return VisibilityService.can_edit(user, obj)
    
    @staticmethod
    def filter_visible(queryset, user):
        """Filter queryset to only visible items."""
        if hasattr(queryset.model, 'objects') and hasattr(queryset.model.objects, 'visible_to'):
            return queryset.model.objects.visible_to(user)
        return queryset
```

---

## 4. Phase 2: Notifications Application

### 4.1 Models

**Duration**: 2 days

**apps/notifications/models/notification.py**
```python
"""Notification models."""
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel

class Notification(BaseModel):
    """User notification record."""
    
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('action', 'Action Required'),
    ]
    
    CHANNEL_CHOICES = [
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications'
    )
    
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Link to related object
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    action_url = models.URLField(blank=True)
    
    # Status tracking
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    
    # Delivery tracking
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(max_length=20, default='pending')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient}"
    
    def mark_as_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
```

**apps/notifications/models/preferences.py**
```python
"""Notification preferences model."""
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel

class NotificationPreference(BaseModel):
    """User notification preferences."""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    
    # Notification types
    notify_on_policy_updates = models.BooleanField(default=True)
    notify_on_claim_updates = models.BooleanField(default=True)
    notify_on_payment_due = models.BooleanField(default=True)
    notify_on_system_updates = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Preferences for {self.user}"
```

### 4.2 Services

**apps/notifications/services/notification_service.py**
```python
"""Notification service for creating and managing notifications."""
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from ..models import Notification, NotificationPreference

class NotificationService:
    """Service for notification operations."""
    
    def __init__(self, user=None):
        self.user = user
    
    def create_notification(self, recipient, title, message, 
                           notification_type='info', 
                           related_object=None,
                           action_url='',
                           channels=None):
        """Create and send a notification."""
        
        # Get user preferences
        prefs = self._get_preferences(recipient)
        
        # Determine channels
        if channels is None:
            channels = self._get_enabled_channels(prefs)
        
        notifications = []
        for channel in channels:
            notification = Notification.objects.create(
                recipient=recipient,
                sender=self.user,
                title=title,
                message=message,
                notification_type=notification_type,
                channel=channel,
                action_url=action_url,
                content_type=ContentType.objects.get_for_model(related_object) if related_object else None,
                object_id=related_object.pk if related_object else None,
            )
            notifications.append(notification)
            
            # Trigger delivery
            self._deliver_notification(notification, channel)
        
        return notifications
    
    def get_unread_count(self, user):
        """Get count of unread notifications."""
        return Notification.objects.filter(
            recipient=user, 
            is_read=False,
            is_archived=False
        ).count()
    
    def mark_all_as_read(self, user):
        """Mark all notifications as read for user."""
        Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    def _get_preferences(self, user):
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        return prefs
    
    def _get_enabled_channels(self, prefs):
        channels = []
        if prefs.in_app_enabled:
            channels.append('in_app')
        if prefs.email_enabled:
            channels.append('email')
        return channels
    
    def _deliver_notification(self, notification, channel):
        """Deliver notification through specified channel."""
        from .delivery_service import DeliveryService
        DeliveryService().deliver(notification, channel)
```

### 4.3 Views

**apps/notifications/views.py**
```python
"""Notification views."""
from django.http import JsonResponse
from apps.core.views.base import (
    BaseListView, BaseDetailView, 
    AuthenticatedAPIView, LoginRequiredMixin
)
from .models import Notification
from .services import NotificationService

class NotificationListView(LoginRequiredMixin, BaseListView):
    """List user notifications."""
    template_name = 'notifications/list.html'
    model = Notification
    paginate_by = 20
    page_title = 'Notifications'
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
            is_archived=False
        )

class NotificationAPIView(AuthenticatedAPIView):
    """API endpoints for notifications."""
    
    def get(self, request):
        """Get notifications for current user."""
        service = NotificationService(request.user)
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_archived=False
        )[:20]
        
        return self.json_success(data={
            'notifications': [n.to_dict() for n in notifications],
            'unread_count': service.get_unread_count(request.user)
        })
    
    def post(self, request):
        """Mark notification as read."""
        notification_id = request.POST.get('id')
        action = request.POST.get('action', 'read')
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=request.user
            )
            
            if action == 'read':
                notification.mark_as_read()
            elif action == 'archive':
                notification.is_archived = True
                notification.save()
            
            return self.json_success('Notification updated')
        except Notification.DoesNotExist:
            return self.json_not_found()
```

### 4.4 URLs

**apps/notifications/urls.py**
```python
"""Notification URL configuration."""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('api/', views.NotificationAPIView.as_view(), name='api'),
    path('preferences/', views.NotificationPreferencesView.as_view(), name='preferences'),
    path('<int:pk>/read/', views.MarkAsReadView.as_view(), name='mark_read'),
]
```

---

## 5. Phase 3: Search Application

### 5.1 Models

**Duration**: 2 days

**apps/search/models/search_index.py**
```python
"""Search index model for caching searchable content."""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from apps.core.models import BaseModel

class SearchIndex(BaseModel):
    """Cached search index for fast lookups."""
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    
    # Indexed content
    title = models.CharField(max_length=500, db_index=True)
    subtitle = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    
    # Metadata
    model_name = models.CharField(max_length=100, db_index=True)
    icon = models.CharField(max_length=50, default='file')
    url = models.URLField(blank=True)
    
    # Visibility (denormalized for performance)
    visibility = models.CharField(max_length=20, default='private', db_index=True)
    owner_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    
    # Search ranking
    weight = models.IntegerField(default=1)
    
    class Meta:
        unique_together = ['content_type', 'object_id']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['model_name', 'visibility']),
        ]
    
    def __str__(self):
        return f"{self.model_name}: {self.title}"
```

**apps/search/models/search_history.py**
```python
"""Search history for analytics and suggestions."""
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel

class SearchHistory(BaseModel):
    """User search history."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='search_history'
    )
    query = models.CharField(max_length=500)
    results_count = models.IntegerField(default=0)
    filters_used = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Search histories'
```

### 5.2 Services

**apps/search/services/search_service.py**
```python
"""Global search service."""
from django.db.models import Q
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from apps.core.mixins import SearchableMixin
from ..models import SearchIndex, SearchHistory

class SearchService:
    """
    Global search service that queries across all models.
    """
    
    # Registry of searchable models
    _registered_models = []
    
    def __init__(self, user=None):
        self.user = user
    
    @classmethod
    def register_model(cls, model):
        """Register a model for global search."""
        if issubclass(model, SearchableMixin):
            cls._registered_models.append(model)
    
    @classmethod
    def register_all_models(cls):
        """Auto-register all models with SearchableMixin."""
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                if issubclass(model, SearchableMixin) and model not in cls._registered_models:
                    cls._registered_models.append(model)
    
    def search(self, query, model_filter=None, limit=50, filters=None):
        """
        Search across all registered models.
        
        Args:
            query: Search query string
            model_filter: Optional list of model names to search
            limit: Maximum results per model
            filters: Additional filters dict
            
        Returns:
            dict with categorized results
        """
        results = {
            'query': query,
            'total': 0,
            'categories': {},
            'all': []
        }
        
        if not query or len(query) < 2:
            return results
        
        # Search each registered model
        for model in self._registered_models:
            model_name = model._meta.verbose_name_plural.title()
            
            if model_filter and model._meta.model_name not in model_filter:
                continue
            
            # Get base queryset with visibility filtering
            queryset = model.objects.all()
            if hasattr(model.objects, 'visible_to') and self.user:
                queryset = model.objects.visible_to(self.user)
            
            # Perform search
            model_results = model.search(query, queryset, limit=limit)
            
            if model_results.exists():
                category_results = []
                for obj in model_results:
                    result = obj.to_search_result()
                    result['model'] = model._meta.model_name
                    category_results.append(result)
                    results['all'].append(result)
                
                results['categories'][model_name] = category_results
                results['total'] += len(category_results)
        
        # Sort all results by relevance
        results['all'].sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Log search
        self._log_search(query, results['total'], filters)
        
        return results
    
    def suggestions(self, query, limit=5):
        """Get search suggestions based on query."""
        suggestions = set()
        
        for model in self._registered_models:
            model_suggestions = model.search_suggestions(query, limit=3)
            suggestions.update(model_suggestions)
        
        return list(suggestions)[:limit]
    
    def _log_search(self, query, results_count, filters):
        """Log search to history."""
        if self.user and self.user.is_authenticated:
            SearchHistory.objects.create(
                user=self.user,
                query=query,
                results_count=results_count,
                filters_used=filters or {}
            )
```

### 5.3 Views

**apps/search/views.py**
```python
"""Search views."""
from django.http import JsonResponse
from apps.core.views.base import (
    BaseTemplateView, AuthenticatedAPIView, LoginRequiredMixin
)
from .services import SearchService

class GlobalSearchView(LoginRequiredMixin, BaseTemplateView):
    """Global search page."""
    template_name = 'search/global.html'
    page_title = 'Search'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        
        if query:
            service = SearchService(self.request.user)
            context['results'] = service.search(query)
            context['query'] = query
        
        return context

class SearchAPIView(AuthenticatedAPIView):
    """Search API endpoint for AJAX requests."""
    
    def get(self, request):
        query = request.GET.get('q', '')
        model_filter = request.GET.getlist('models')
        
        service = SearchService(request.user)
        
        if request.GET.get('suggestions'):
            suggestions = service.suggestions(query)
            return self.json_success(data={'suggestions': suggestions})
        
        results = service.search(
            query=query,
            model_filter=model_filter if model_filter else None,
            limit=int(request.GET.get('limit', 20))
        )
        
        return self.json_success(data=results)
```

### 5.4 URLs

**apps/search/urls.py**
```python
"""Search URL configuration."""
from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.GlobalSearchView.as_view(), name='global'),
    path('api/', views.SearchAPIView.as_view(), name='api'),
    path('suggestions/', views.SuggestionsView.as_view(), name='suggestions'),
]
```

---

## 6. Phase 4: Trash Application

### 6.1 Models

**Duration**: 1 day

**apps/trash/models/trash_registry.py**
```python
"""Trash registry for tracking all trashed items."""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from apps.core.models import BaseModel

class TrashRegistry(BaseModel):
    """
    Central registry of all trashed items across all models.
    Provides unified trash view and management.
    """
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    
    # Cached data for display
    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=50, default='file')
    
    # Trash metadata
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='trashed_items'
    )
    trash_reason = models.TextField(blank=True)
    original_data = models.JSONField(default=dict)
    
    # Expiry
    expires_at = models.DateTimeField(db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['content_type', 'object_id']
        verbose_name_plural = 'Trash registry'
    
    def __str__(self):
        return f"Trashed: {self.title}"
    
    def get_object(self):
        """Get the actual trashed object."""
        model = self.content_type.model_class()
        try:
            return model.all_objects.get(pk=self.object_id)
        except model.DoesNotExist:
            return None
    
    def restore(self):
        """Restore the object from trash."""
        obj = self.get_object()
        if obj and hasattr(obj, 'restore_from_trash'):
            obj.restore_from_trash()
            self.delete()
            return True
        return False
    
    def permanent_delete(self):
        """Permanently delete the object."""
        obj = self.get_object()
        if obj:
            obj.delete(force=True)
        self.delete()
```

### 6.2 Services

**apps/trash/services/trash_service.py**
```python
"""Trash management service."""
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.apps import apps
from datetime import timedelta
from apps.core.mixins import TrashableMixin
from ..models import TrashRegistry

class TrashService:
    """
    Unified trash management service.
    """
    
    def __init__(self, user=None):
        self.user = user
    
    def get_all_trashed(self, model_filter=None):
        """Get all trashed items visible to user."""
        queryset = TrashRegistry.objects.all()
        
        if model_filter:
            content_types = ContentType.objects.filter(model__in=model_filter)
            queryset = queryset.filter(content_type__in=content_types)
        
        if self.user and not self.user.is_superuser:
            queryset = queryset.filter(trashed_by=self.user)
        
        return queryset
    
    def get_statistics(self):
        """Get trash statistics."""
        queryset = self.get_all_trashed()
        
        now = timezone.now()
        return {
            'total': queryset.count(),
            'expiring_soon': queryset.filter(
                expires_at__lte=now + timedelta(days=7)
            ).count(),
            'expired': queryset.filter(expires_at__lte=now).count(),
            'by_type': self._group_by_type(queryset),
        }
    
    def restore_item(self, registry_id):
        """Restore an item from trash."""
        try:
            registry = TrashRegistry.objects.get(id=registry_id)
            
            # Check permission
            if not self._can_restore(registry):
                raise PermissionError("Cannot restore this item")
            
            return registry.restore()
        except TrashRegistry.DoesNotExist:
            return False
    
    def permanent_delete_item(self, registry_id):
        """Permanently delete an item."""
        try:
            registry = TrashRegistry.objects.get(id=registry_id)
            
            if not self._can_delete(registry):
                raise PermissionError("Cannot delete this item")
            
            registry.permanent_delete()
            return True
        except TrashRegistry.DoesNotExist:
            return False
    
    def empty_expired(self):
        """Delete all expired items."""
        expired = TrashRegistry.objects.filter(expires_at__lte=timezone.now())
        count = expired.count()
        
        for registry in expired:
            registry.permanent_delete()
        
        return count
    
    def _can_restore(self, registry):
        if self.user.is_superuser:
            return True
        return registry.trashed_by == self.user
    
    def _can_delete(self, registry):
        return self._can_restore(registry)
    
    def _group_by_type(self, queryset):
        result = {}
        for registry in queryset.select_related('content_type'):
            model_name = registry.content_type.model
            result[model_name] = result.get(model_name, 0) + 1
        return result
```

### 6.3 Views

**apps/trash/views.py**
```python
"""Trash views."""
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from apps.core.views.base import (
    BaseListView, BaseTemplateView,
    AuthenticatedAPIView, LoginRequiredMixin
)
from .models import TrashRegistry
from .services import TrashService

class TrashListView(LoginRequiredMixin, BaseListView):
    """List all trashed items."""
    template_name = 'trash/list.html'
    model = TrashRegistry
    paginate_by = 20
    page_title = 'Trash'
    
    def get_queryset(self):
        service = TrashService(self.request.user)
        model_filter = self.request.GET.getlist('type')
        return service.get_all_trashed(model_filter if model_filter else None)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = TrashService(self.request.user)
        context['statistics'] = service.get_statistics()
        return context

class RestoreItemView(LoginRequiredMixin, BaseTemplateView):
    """Restore item from trash."""
    
    def post(self, request, pk):
        service = TrashService(request.user)
        
        if service.restore_item(pk):
            messages.success(request, 'Item restored successfully.')
        else:
            messages.error(request, 'Failed to restore item.')
        
        return redirect('trash:list')

class TrashAPIView(AuthenticatedAPIView):
    """Trash API endpoints."""
    
    def get(self, request):
        service = TrashService(request.user)
        return self.json_success(data=service.get_statistics())
    
    def post(self, request):
        action = request.POST.get('action')
        item_id = request.POST.get('id')
        
        service = TrashService(request.user)
        
        if action == 'restore':
            success = service.restore_item(item_id)
        elif action == 'delete':
            success = service.permanent_delete_item(item_id)
        elif action == 'empty_expired':
            count = service.empty_expired()
            return self.json_success(f'Deleted {count} expired items')
        else:
            return self.json_error('Invalid action')
        
        if success:
            return self.json_success('Operation completed')
        return self.json_error('Operation failed')
```

### 6.4 URLs

**apps/trash/urls.py**
```python
"""Trash URL configuration."""
from django.urls import path
from . import views

app_name = 'trash'

urlpatterns = [
    path('', views.TrashListView.as_view(), name='list'),
    path('api/', views.TrashAPIView.as_view(), name='api'),
    path('<int:pk>/restore/', views.RestoreItemView.as_view(), name='restore'),
    path('<int:pk>/delete/', views.PermanentDeleteView.as_view(), name='delete'),
    path('empty/', views.EmptyTrashView.as_view(), name='empty'),
]
```

---

## 7. UI/UX Implementation

### 7.1 Design System Integration

All new apps will use the existing design system from `static/css/variables.css`:

- **Colors**: Use `--color-primary-*` and semantic colors
- **Typography**: System font stack with proper sizing
- **Spacing**: Consistent spacing scale
- **Shadows**: Minimal, subtle shadows
- **Transitions**: Smooth 150-300ms transitions

### 7.2 Template Structure

Create templates following existing patterns:

```
templates/
├── notifications/
│   ├── list.html
│   ├── preferences.html
│   └── partials/
│       ├── notification_item.html
│       └── notification_dropdown.html
│
├── search/
│   ├── global.html
│   └── partials/
│       ├── search_result.html
│       ├── search_filters.html
│       └── search_modal.html
│
├── trash/
│   ├── list.html
│   └── partials/
│       ├── trash_item.html
│       └── trash_stats.html
```

### 7.3 CSS Files

Create modular CSS files:

```
static/css/
├── notifications.css
├── search.css
└── trash.css
```

### 7.4 Key UI Components

**Global Search Modal** (Cmd/Ctrl+K):
- Floating modal with blur backdrop
- Real-time search with debouncing
- Keyboard navigation
- Category grouping
- Recent searches

**Notification Bell** (Header):
- Unread count badge
- Dropdown with latest notifications
- Mark all as read
- Link to full notifications page

**Trash Sidebar Widget**:
- Storage usage indicator
- Quick stats
- Empty trash button
- Expiring soon alerts

---

## 8. Testing Requirements

### 8.1 Unit Tests

**tests/unit/**
```
├── test_notification_service.py
├── test_search_service.py
├── test_trash_service.py
├── test_visibility_service.py
└── test_models.py
```

Coverage targets:
- Services: 95%
- Models: 90%
- Views: 85%

### 8.2 Integration Tests

**tests/integration/**
```
├── test_notification_delivery.py
├── test_search_indexing.py
├── test_trash_workflow.py
└── test_visibility_controls.py
```

### 8.3 Performance Tests

- Search response time < 100ms for 10,000 indexed items
- Notification delivery < 500ms
- Trash operations < 200ms

---

## 9. Configuration Updates

### 9.1 Settings Update

Add to `config/settings/base.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    'apps.notifications',
    'apps.search',
    'apps.trash',
]

# Notification settings
NOTIFICATION_CHANNELS = ['in_app', 'email']
NOTIFICATION_EMAIL_ENABLED = True

# Search settings
SEARCH_MIN_QUERY_LENGTH = 2
SEARCH_RESULTS_LIMIT = 50
SEARCH_CACHE_TIMEOUT = 300

# Trash settings
TRASH_RETENTION_DAYS = 30
TRASH_AUTO_EMPTY = True
```

### 9.2 URL Updates

Add to `config/urls.py`:

```python
urlpatterns = [
    # ... existing patterns
    path('notifications/', include('apps.notifications.urls')),
    path('search/', include('apps.search.urls')),
    path('trash/', include('apps.trash.urls')),
]
```

---

## 10. Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | 3 days | Folder structure, Visibility system |
| Phase 2: Notifications | 5 days | Models, Services, Views, Templates |
| Phase 3: Search | 5 days | Global search, Indexing, UI |
| Phase 4: Trash | 3 days | Trash management, Restoration |
| Phase 5: UI Polish | 4 days | Animations, Responsiveness |
| Phase 6: Testing | 4 days | Unit, Integration, Performance |
| Phase 7: Documentation | 2 days | API docs, Usage guides |

**Total**: ~26 days

---

## 11. Quality Checklist

- [ ] 90%+ test coverage
- [ ] WCAG 2.1 AA compliance
- [ ] Sub-100ms search response
- [ ] Mobile responsive layouts
- [ ] Keyboard accessibility
- [ ] Error handling and logging
- [ ] API documentation
- [ ] User documentation

---

## 12. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-12-25 | System | Initial implementation plan |
