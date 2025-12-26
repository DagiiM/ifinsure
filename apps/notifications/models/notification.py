"""
Notification model for user notifications.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from apps.core.models import SimpleBaseModel


class NotificationManager(models.Manager):
    """Custom manager for notifications."""
    
    def unread(self):
        """Get unread notifications."""
        return self.filter(is_read=False, is_archived=False)
    
    def for_user(self, user):
        """Get notifications for a specific user."""
        return self.filter(recipient=user)
    
    def unread_for_user(self, user):
        """Get unread notifications for a specific user."""
        return self.for_user(user).unread()


class Notification(SimpleBaseModel):
    """
    User notification record.
    
    Supports multiple notification types and channels,
    with tracking for read status and delivery.
    """
    
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
    
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    # Recipient and sender
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='User who receives this notification'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        help_text='User who triggered this notification (if any)'
    )
    
    # Notification content
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='info',
        db_index=True
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default='in_app',
        db_index=True
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Icon for visual display
    icon = models.CharField(
        max_length=50,
        default='bell',
        help_text='Icon name for display'
    )
    icon_color = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text='Icon color class'
    )
    
    # Link to related object using GenericForeignKey
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action URL for click handling
    action_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL to navigate to when notification is clicked'
    )
    
    # Status tracking
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether the notification has been read'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the notification was read'
    )
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether the notification is archived'
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # Delivery tracking
    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_error = models.TextField(blank=True, default='')
    
    # Priority for sorting
    priority = models.IntegerField(
        default=0,
        db_index=True,
        help_text='Higher priority notifications appear first'
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Notification expires and disappears after this time'
    )
    
    objects = NotificationManager()
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'is_archived']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"{self.title} - {self.recipient}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def archive(self):
        """Archive the notification."""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            self.save(update_fields=['is_archived', 'archived_at', 'updated_at'])
    
    def unarchive(self):
        """Unarchive the notification."""
        if self.is_archived:
            self.is_archived = False
            self.archived_at = None
            self.save(update_fields=['is_archived', 'archived_at', 'updated_at'])
    
    @property
    def is_expired(self):
        """Check if notification has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def time_since_created(self):
        """Get human-readable time since creation."""
        delta = timezone.now() - self.created_at
        
        if delta.days > 365:
            years = delta.days // 365
            return f"{years}y ago"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months}mo ago"
        elif delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    
    def to_dict(self):
        """Convert notification to dictionary for JSON responses."""
        return {
            'id': self.pk,
            'type': self.notification_type,
            'channel': self.channel,
            'title': self.title,
            'message': self.message,
            'icon': self.icon,
            'icon_color': self.icon_color,
            'action_url': self.action_url,
            'is_read': self.is_read,
            'is_archived': self.is_archived,
            'priority': self.priority,
            'time_ago': self.time_since_created,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }
    
    def get_icon_class(self):
        """Get CSS class for icon based on notification type."""
        icon_classes = {
            'info': 'text-info',
            'success': 'text-success',
            'warning': 'text-warning',
            'error': 'text-danger',
            'action': 'text-primary',
        }
        return self.icon_color or icon_classes.get(self.notification_type, 'text-secondary')
