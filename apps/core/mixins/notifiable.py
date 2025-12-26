"""
Notifiable Mixin - Notify creators/owners of resource changes.

Provides:
- Automatic notifications on CRUD operations
- Configurable notification channels
- Subscription management
- Change tracking for notifications
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class NotifiableMixin(models.Model):
    """
    Mixin to notify resource creators/owners of changes.
    
    Features:
    - Tracks who should be notified
    - Configurable notification preferences
    - Supports multiple notification channels (email, SMS, push, in-app)
    - Change tracking for meaningful notifications
    
    Usage:
        class Policy(NotifiableMixin, BaseModel):
            NOTIFY_ON = ['create', 'update', 'delete']
            NOTIFY_CHANNELS = ['email', 'in_app']
            NOTIFY_FIELDS = ['status', 'premium_amount']  # Only notify on these field changes
            
            customer = models.ForeignKey(User, ...)
            status = models.CharField(...)
            
            def get_notification_recipients(self):
                return [self.customer]
    """
    
    # Notification preferences
    notifications_enabled = models.BooleanField(
        default=True,
        help_text='Whether notifications are enabled for this resource'
    )
    
    # Track last notification
    last_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the last notification was sent'
    )
    
    # Subscribers (users watching this resource)
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='%(class)s_watching',
        help_text='Users watching this resource for changes'
    )
    
    class Meta:
        abstract = True
    
    # Override in subclass - which actions trigger notifications
    NOTIFY_ON = ['create', 'update', 'delete', 'status_change']
    
    # Override in subclass - notification channels to use
    NOTIFY_CHANNELS = ['email', 'in_app']
    
    # Override in subclass - only notify when these fields change
    NOTIFY_FIELDS = []
    
    # Override in subclass - minimum time between notifications (seconds)
    NOTIFY_COOLDOWN = 0
    
    def get_notification_recipients(self):
        """
        Override this to return list of users to notify.
        Default returns watchers + creator if AccountabilityMixin is used.
        """
        recipients = list(self.watchers.all())
        
        # Add creator if using AccountabilityMixin
        if hasattr(self, 'created_by') and self.created_by:
            if self.created_by not in recipients:
                recipients.append(self.created_by)
        
        return recipients
    
    def get_notification_context(self, action, changed_fields=None):
        """
        Get context for notification templates.
        Override to customize notification content.
        """
        return {
            'object': self,
            'object_type': self._meta.verbose_name,
            'object_id': self.pk,
            'action': action,
            'changed_fields': changed_fields or [],
            'timestamp': timezone.now(),
        }
    
    def should_notify(self, action, changed_fields=None):
        """Check if notification should be sent."""
        if not self.notifications_enabled:
            return False
        
        if action not in self.NOTIFY_ON:
            return False
        
        # Check cooldown
        if self.NOTIFY_COOLDOWN and self.last_notified_at:
            from datetime import timedelta
            cooldown_until = self.last_notified_at + timedelta(seconds=self.NOTIFY_COOLDOWN)
            if timezone.now() < cooldown_until:
                return False
        
        # If NOTIFY_FIELDS is set, only notify if those fields changed
        if self.NOTIFY_FIELDS and changed_fields:
            if not any(f in self.NOTIFY_FIELDS for f in changed_fields):
                return False
        
        return True
    
    def notify(self, action, changed_fields=None, actor=None):
        """
        Send notifications to all recipients.
        
        Args:
            action: 'create', 'update', 'delete', 'status_change'
            changed_fields: List of field names that changed
            actor: User who performed the action
        """
        if not self.should_notify(action, changed_fields):
            return
        
        recipients = self.get_notification_recipients()
        if not recipients:
            return
        
        # Don't notify the actor of their own changes
        if actor and actor in recipients:
            recipients.remove(actor)
        
        if not recipients:
            return
        
        context = self.get_notification_context(action, changed_fields)
        context['actor'] = actor
        
        # Send through each channel
        for channel in self.NOTIFY_CHANNELS:
            self._send_notification(channel, recipients, context)
        
        # Update last notified
        self.last_notified_at = timezone.now()
        self.save(update_fields=['last_notified_at'])
    
    def _send_notification(self, channel, recipients, context):
        """
        Send notification through specified channel.
        Override or extend for custom notification logic.
        """
        # Import here to avoid circular imports
        try:
            if channel == 'email':
                self._send_email_notification(recipients, context)
            elif channel == 'in_app':
                self._send_in_app_notification(recipients, context)
            elif channel == 'sms':
                self._send_sms_notification(recipients, context)
            elif channel == 'push':
                self._send_push_notification(recipients, context)
        except Exception as e:
            # Log but don't fail the main operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Failed to send {channel} notification: {e}')
    
    def _send_email_notification(self, recipients, context):
        """Send email notification. Override for custom implementation."""
        pass  # Implement with your email service
    
    def _send_in_app_notification(self, recipients, context):
        """Send in-app notification. Override for custom implementation."""
        pass  # Implement with your notification model
    
    def _send_sms_notification(self, recipients, context):
        """Send SMS notification. Override for custom implementation."""
        pass  # Implement with your SMS service
    
    def _send_push_notification(self, recipients, context):
        """Send push notification. Override for custom implementation."""
        pass  # Implement with your push service
    
    def add_watcher(self, user):
        """Add a user to watch this resource."""
        self.watchers.add(user)
    
    def remove_watcher(self, user):
        """Remove a user from watching this resource."""
        self.watchers.remove(user)
    
    def get_watchers(self):
        """Get all users watching this resource."""
        return self.watchers.all()
