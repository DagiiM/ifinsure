"""
Notifications app - Real-time user notifications.
"""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notifications'
    
    def ready(self):
        # Import signals to register them
        try:
            from .models import signals  # noqa
        except ImportError:
            pass
