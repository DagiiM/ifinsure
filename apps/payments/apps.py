"""
Payments app configuration.
"""
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'Payments'
    
    def ready(self):
        # Import signal handlers
        import apps.payments.handlers  # noqa
