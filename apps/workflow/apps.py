"""
Workflow app configuration.
"""
from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflow'
    verbose_name = 'Workflow & Agent Management'
    
    def ready(self):
        # Import signals
        import apps.workflow.signals  # noqa
