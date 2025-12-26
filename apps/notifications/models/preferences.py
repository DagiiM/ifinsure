"""
Notification preferences model.
"""
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import SimpleBaseModel


class NotificationPreference(SimpleBaseModel):
    """
    User notification preferences.
    
    Controls which notifications a user receives and through which channels.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # ===== Channel preferences =====
    email_enabled = models.BooleanField(
        default=True,
        help_text='Receive email notifications'
    )
    sms_enabled = models.BooleanField(
        default=False,
        help_text='Receive SMS notifications'
    )
    push_enabled = models.BooleanField(
        default=True,
        help_text='Receive push notifications'
    )
    in_app_enabled = models.BooleanField(
        default=True,
        help_text='Receive in-app notifications'
    )
    
    # ===== Notification type preferences =====
    # Policy notifications
    notify_policy_created = models.BooleanField(default=True)
    notify_policy_updated = models.BooleanField(default=True)
    notify_policy_expiring = models.BooleanField(default=True)
    notify_policy_expired = models.BooleanField(default=True)
    
    # Claim notifications
    notify_claim_submitted = models.BooleanField(default=True)
    notify_claim_updated = models.BooleanField(default=True)
    notify_claim_approved = models.BooleanField(default=True)
    notify_claim_rejected = models.BooleanField(default=True)
    
    # Payment notifications
    notify_payment_due = models.BooleanField(default=True)
    notify_payment_received = models.BooleanField(default=True)
    notify_payment_overdue = models.BooleanField(default=True)
    
    # System notifications
    notify_system_updates = models.BooleanField(default=True)
    notify_security_alerts = models.BooleanField(default=True)
    notify_promotions = models.BooleanField(default=False)
    
    # ===== Quiet hours =====
    quiet_hours_enabled = models.BooleanField(
        default=False,
        help_text='Enable quiet hours (no notifications during specified time)'
    )
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text='Start of quiet hours (e.g., 22:00)'
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text='End of quiet hours (e.g., 07:00)'
    )
    
    # ===== Digest preferences =====
    email_digest_enabled = models.BooleanField(
        default=False,
        help_text='Receive email digest instead of individual emails'
    )
    email_digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='daily'
    )
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Notification preferences for {self.user}"
    
    def get_enabled_channels(self):
        """Get list of enabled notification channels."""
        channels = []
        if self.in_app_enabled:
            channels.append('in_app')
        if self.email_enabled:
            channels.append('email')
        if self.sms_enabled:
            channels.append('sms')
        if self.push_enabled:
            channels.append('push')
        return channels
    
    def is_notification_enabled(self, notification_key):
        """
        Check if a specific notification type is enabled.
        
        Args:
            notification_key: e.g., 'policy_created', 'claim_updated'
        """
        field_name = f'notify_{notification_key}'
        return getattr(self, field_name, True)
    
    def is_in_quiet_hours(self):
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_enabled:
            return False
        
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        from django.utils import timezone
        now = timezone.localtime().time()
        
        # Handle overnight quiet hours (e.g., 22:00 to 07:00)
        if self.quiet_hours_start > self.quiet_hours_end:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        else:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
    
    def should_send_notification(self, notification_key, channel):
        """
        Determine if a notification should be sent.
        
        Args:
            notification_key: Type of notification
            channel: Delivery channel
        """
        # Check if channel is enabled
        channel_field = f'{channel}_enabled'
        if not getattr(self, channel_field, False):
            return False
        
        # Check if notification type is enabled
        if not self.is_notification_enabled(notification_key):
            return False
        
        # Check quiet hours (only for push and in_app)
        if channel in ['push', 'in_app'] and self.is_in_quiet_hours():
            return False
        
        return True


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences when a new user is created."""
    if created:
        NotificationPreference.objects.get_or_create(user=instance)
