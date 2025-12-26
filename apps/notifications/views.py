"""
Notification views.
"""
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.db import models

from apps.core.views.base import (
    BaseListView, BaseTemplateView, BaseUpdateView,
    AuthenticatedAPIView, LoginRequiredMixin, BaseContextMixin
)
from .models import Notification, NotificationPreference
from .services import NotificationService


class NotificationListView(LoginRequiredMixin, BaseListView):
    """List user notifications."""
    
    template_name = 'notifications/list.html'
    model = Notification
    paginate_by = 20
    page_title = 'Notifications'
    context_object_name = 'notifications'
    
    def get_queryset(self):
        queryset = Notification.objects.filter(
            recipient=self.request.user,
            is_active=True
        )
        
        # Filter by read status
        status = self.request.GET.get('status')
        if status == 'unread':
            queryset = queryset.filter(is_read=False)
        elif status == 'read':
            queryset = queryset.filter(is_read=True)
        
        # Filter by type
        notification_type = self.request.GET.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Include/exclude archived
        if self.request.GET.get('include_archived') != 'true':
            queryset = queryset.filter(is_archived=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = NotificationService(self.request.user)
        context['unread_count'] = service.get_unread_count(self.request.user)
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_type'] = self.request.GET.get('type', '')
        return context


class NotificationDetailView(LoginRequiredMixin, BaseTemplateView):
    """View a single notification and mark as read."""
    
    template_name = 'notifications/detail.html'
    
    def get(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user
        )
        
        # Mark as read
        notification.mark_as_read()
        
        # If there's an action URL, redirect to it
        if notification.action_url:
            return redirect(notification.action_url)
        
        return super().get(request, pk=pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification'] = get_object_or_404(
            Notification,
            pk=self.kwargs['pk'],
            recipient=self.request.user
        )
        return context


class MarkAsReadView(LoginRequiredMixin, View):
    """Mark a notification as read."""
    
    def post(self, request, pk):
        service = NotificationService(request.user)
        success = service.mark_as_read(pk, request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': success})
        
        if success:
            messages.success(request, 'Notification marked as read.')
        
        return redirect('notifications:list')


class MarkAllAsReadView(LoginRequiredMixin, View):
    """Mark all notifications as read."""
    
    def post(self, request):
        service = NotificationService(request.user)
        count = service.mark_all_as_read(request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'count': count})
        
        messages.success(request, f'Marked {count} notifications as read.')
        return redirect('notifications:list')


class ArchiveNotificationView(LoginRequiredMixin, View):
    """Archive a notification."""
    
    def post(self, request, pk):
        service = NotificationService(request.user)
        success = service.archive_notification(pk, request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': success})
        
        if success:
            messages.success(request, 'Notification archived.')
        
        return redirect('notifications:list')


class DeleteNotificationView(LoginRequiredMixin, View):
    """Delete a notification."""
    
    def post(self, request, pk):
        service = NotificationService(request.user)
        success = service.delete_notification(pk, request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': success})
        
        if success:
            messages.success(request, 'Notification deleted.')
        
        return redirect('notifications:list')


class NotificationPreferencesView(BaseUpdateView):
    """Update notification preferences."""
    
    template_name = 'notifications/preferences.html'
    model = NotificationPreference
    page_title = 'Notification Preferences'
    success_message = 'Preferences updated successfully.'
    
    fields = [
        'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
        'notify_policy_created', 'notify_policy_updated', 
        'notify_policy_expiring', 'notify_policy_expired',
        'notify_claim_submitted', 'notify_claim_updated',
        'notify_claim_approved', 'notify_claim_rejected',
        'notify_payment_due', 'notify_payment_received', 'notify_payment_overdue',
        'notify_system_updates', 'notify_security_alerts', 'notify_promotions',
        'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
        'email_digest_enabled', 'email_digest_frequency',
    ]
    
    def get_object(self):
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return prefs
    
    def get_success_url(self):
        from django.urls import reverse
        return reverse('notifications:preferences')


class NotificationAPIView(AuthenticatedAPIView):
    """API endpoints for notifications."""
    
    def get(self, request):
        """Get notifications for current user."""
        service = NotificationService(request.user)
        
        # Get parameters
        limit = int(request.GET.get('limit', 10))
        include_archived = request.GET.get('include_archived') == 'true'
        
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_active=True
        )
        
        if not include_archived:
            notifications = notifications.filter(is_archived=False)
        
        notifications = notifications[:limit]
        
        return self.json_success(data={
            'notifications': [n.to_dict() for n in notifications],
            'unread_count': service.get_unread_count(request.user)
        })
    
    def post(self, request):
        """Handle notification actions."""
        notification_id = request.POST.get('id')
        action = request.POST.get('action', 'read')
        
        service = NotificationService(request.user)
        
        if action == 'read':
            success = service.mark_as_read(notification_id, request.user)
        elif action == 'read_all':
            count = service.mark_all_as_read(request.user)
            return self.json_success(f'Marked {count} as read')
        elif action == 'archive':
            success = service.archive_notification(notification_id, request.user)
        elif action == 'delete':
            success = service.delete_notification(notification_id, request.user)
        else:
            return self.json_error('Invalid action')
        
        if success:
            return self.json_success('Notification updated')
        return self.json_not_found('Notification not found')


class NotificationDropdownView(LoginRequiredMixin, BaseTemplateView):
    """Render notification dropdown content."""
    
    template_name = 'notifications/partials/dropdown.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = NotificationService(self.request.user)
        
        context['notifications'] = Notification.objects.filter(
            recipient=self.request.user,
            is_archived=False,
            is_active=True
        )[:5]
        context['unread_count'] = service.get_unread_count(self.request.user)
        
        return context
