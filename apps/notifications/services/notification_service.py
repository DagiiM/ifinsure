"""
Notification service for creating and managing notifications.
"""
import logging
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import transaction

from ..models import Notification, NotificationPreference

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for notification operations.
    
    Handles creation, delivery, and management of notifications
    with respect to user preferences.
    """
    
    def __init__(self, user=None):
        """
        Initialize service with optional user context.
        
        Args:
            user: The user performing the action (sender)
        """
        self.user = user
    
    def create_notification(
        self,
        recipient,
        title,
        message,
        notification_type='info',
        notification_key=None,
        related_object=None,
        action_url='',
        icon='bell',
        icon_color='',
        priority=0,
        channels=None,
        expires_at=None
    ):
        """
        Create and send a notification to a user.
        
        Args:
            recipient: User to receive the notification
            title: Notification title
            message: Notification body
            notification_type: 'info', 'success', 'warning', 'error', 'action'
            notification_key: Key for preference lookup (e.g., 'policy_created')
            related_object: Optional related Django model instance
            action_url: URL to navigate to on click
            icon: Icon name for display
            icon_color: CSS class for icon color
            priority: Higher priority = appears first
            channels: List of channels to use (defaults to user preferences)
            expires_at: When notification expires
            
        Returns:
            List of created Notification instances
        """
        # Get user preferences
        prefs = self._get_preferences(recipient)
        
        # Determine channels to use
        if channels is None:
            channels = prefs.get_enabled_channels()
        
        # Filter channels based on preferences if notification_key provided
        if notification_key:
            channels = [
                ch for ch in channels
                if prefs.should_send_notification(notification_key, ch)
            ]
        
        if not channels:
            logger.debug(f"No channels enabled for notification to {recipient}")
            return []
        
        notifications = []
        
        with transaction.atomic():
            for channel in channels:
                notification = Notification.objects.create(
                    recipient=recipient,
                    sender=self.user,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    channel=channel,
                    icon=icon,
                    icon_color=icon_color,
                    action_url=action_url,
                    priority=priority,
                    expires_at=expires_at,
                    content_type=ContentType.objects.get_for_model(related_object) if related_object else None,
                    object_id=related_object.pk if related_object else None,
                )
                notifications.append(notification)
                
                # Trigger delivery for non-in_app channels
                if channel != 'in_app':
                    self._queue_delivery(notification, channel)
        
        return notifications
    
    def create_bulk_notifications(self, recipients, title, message, **kwargs):
        """
        Create notifications for multiple recipients.
        
        Args:
            recipients: List of users or queryset
            title: Notification title
            message: Notification body
            **kwargs: Additional arguments for create_notification
            
        Returns:
            List of all created notifications
        """
        all_notifications = []
        
        for recipient in recipients:
            notifications = self.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                **kwargs
            )
            all_notifications.extend(notifications)
        
        return all_notifications
    
    def get_notifications(self, user, include_archived=False, limit=None):
        """
        Get notifications for a user.
        
        Args:
            user: User to get notifications for
            include_archived: Whether to include archived notifications
            limit: Maximum number to return
            
        Returns:
            QuerySet of notifications
        """
        queryset = Notification.objects.filter(recipient=user)
        
        if not include_archived:
            queryset = queryset.filter(is_archived=False)
        
        # Exclude expired notifications
        queryset = queryset.filter(
            models.Q(expires_at__isnull=True) |
            models.Q(expires_at__gt=timezone.now())
        )
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    def get_unread_count(self, user):
        """Get count of unread notifications for user."""
        return Notification.objects.filter(
            recipient=user,
            is_read=False,
            is_archived=False
        ).filter(
            models.Q(expires_at__isnull=True) |
            models.Q(expires_at__gt=timezone.now())
        ).count()
    
    def mark_as_read(self, notification_id, user):
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of notification
            user: User making the request (for permission check)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    def mark_all_as_read(self, user):
        """Mark all notifications as read for user."""
        count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return count
    
    def archive_notification(self, notification_id, user):
        """Archive a notification."""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.archive()
            return True
        except Notification.DoesNotExist:
            return False
    
    def delete_notification(self, notification_id, user):
        """Delete a notification (soft delete)."""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.soft_delete()
            return True
        except Notification.DoesNotExist:
            return False
    
    def clear_expired(self):
        """Delete all expired notifications."""
        count = Notification.objects.filter(
            expires_at__lte=timezone.now()
        ).delete()[0]
        return count
    
    def _get_preferences(self, user):
        """Get or create notification preferences for user."""
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        return prefs
    
    def _queue_delivery(self, notification, channel):
        """
        Queue notification for delivery through specified channel.
        
        In a production system, this would use Celery or similar.
        For now, we deliver synchronously.
        """
        from .delivery_service import DeliveryService
        
        try:
            DeliveryService().deliver(notification, channel)
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification.id}: {e}")
            notification.delivery_status = 'failed'
            notification.delivery_error = str(e)
            notification.save(update_fields=['delivery_status', 'delivery_error'])


# Import models for Q object
from django.db import models
