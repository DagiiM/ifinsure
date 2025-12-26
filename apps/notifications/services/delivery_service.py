"""
Delivery service for sending notifications through various channels.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class DeliveryService:
    """
    Service for delivering notifications through various channels.
    
    Supports:
    - Email
    - SMS (placeholder)
    - Push notifications (placeholder)
    - In-app (handled separately)
    """
    
    def deliver(self, notification, channel):
        """
        Deliver notification through specified channel.
        
        Args:
            notification: Notification instance
            channel: Delivery channel ('email', 'sms', 'push')
        """
        delivery_methods = {
            'email': self._send_email,
            'sms': self._send_sms,
            'push': self._send_push,
            'in_app': self._mark_delivered,  # In-app is already "delivered"
        }
        
        method = delivery_methods.get(channel)
        if not method:
            logger.warning(f"Unknown delivery channel: {channel}")
            return False
        
        try:
            success = method(notification)
            
            if success:
                notification.delivery_status = 'delivered'
                notification.delivered_at = timezone.now()
            else:
                notification.delivery_status = 'failed'
            
            notification.save(update_fields=['delivery_status', 'delivered_at'])
            return success
            
        except Exception as e:
            logger.error(f"Delivery failed for notification {notification.id}: {e}")
            notification.delivery_status = 'failed'
            notification.delivery_error = str(e)
            notification.save(update_fields=['delivery_status', 'delivery_error'])
            return False
    
    def _send_email(self, notification):
        """Send notification via email."""
        recipient = notification.recipient
        
        if not recipient.email:
            logger.warning(f"No email address for user {recipient.id}")
            return False
        
        try:
            # Render email templates
            context = {
                'notification': notification,
                'recipient': recipient,
                'action_url': notification.action_url,
            }
            
            # Try to render custom template, fall back to plain text
            try:
                html_message = render_to_string(
                    'emails/notification.html',
                    context
                )
            except:
                html_message = None
            
            subject = notification.title
            plain_message = notification.message
            
            from_email = getattr(
                settings,
                'DEFAULT_FROM_EMAIL',
                'noreply@ifinsure.com'
            )
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Email sent to {recipient.email} for notification {notification.id}")
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            raise
    
    def _send_sms(self, notification):
        """
        Send notification via SMS.
        
        This is a placeholder - implement with your SMS provider.
        """
        recipient = notification.recipient
        
        # Get phone number
        phone = getattr(recipient, 'phone', None)
        if not phone:
            logger.warning(f"No phone number for user {recipient.id}")
            return False
        
        # Placeholder for SMS implementation
        # Example with Twilio:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        # message = client.messages.create(
        #     body=notification.message,
        #     from_=settings.TWILIO_PHONE,
        #     to=phone
        # )
        
        logger.info(f"SMS would be sent to {phone}: {notification.message[:50]}...")
        return True
    
    def _send_push(self, notification):
        """
        Send push notification.
        
        This is a placeholder - implement with your push provider.
        """
        # Placeholder for push notification implementation
        # Example with Firebase:
        # from firebase_admin import messaging
        # message = messaging.Message(
        #     notification=messaging.Notification(
        #         title=notification.title,
        #         body=notification.message,
        #     ),
        #     token=recipient.push_token,
        # )
        # messaging.send(message)
        
        logger.info(f"Push notification would be sent: {notification.title}")
        return True
    
    def _mark_delivered(self, notification):
        """Mark in-app notification as delivered."""
        # In-app notifications are considered delivered immediately
        return True
    
    def send_digest(self, user, notifications):
        """
        Send a digest email with multiple notifications.
        
        Args:
            user: Recipient user
            notifications: List of notifications to include
        """
        if not notifications:
            return False
        
        if not user.email:
            return False
        
        try:
            context = {
                'user': user,
                'notifications': notifications,
                'count': len(notifications),
            }
            
            html_message = render_to_string(
                'emails/notification_digest.html',
                context
            )
            
            subject = f"You have {len(notifications)} new notifications"
            
            send_mail(
                subject=subject,
                message=f"You have {len(notifications)} new notifications. View them in the app.",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ifinsure.com'),
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Digest email failed for user {user.id}: {e}")
            return False
