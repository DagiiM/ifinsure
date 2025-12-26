"""
Trash app - Unified trash management.
"""
from django.apps import AppConfig


class TrashConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.trash'
    verbose_name = 'Trash Management'
    
    def ready(self):
        # Import signals for trash tracking
        try:
            from .models import signals  # noqa
        except ImportError:
            pass
