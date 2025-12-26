"""
Search app - Global search across all models.
"""
from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.search'
    verbose_name = 'Global Search'
    
    def ready(self):
        # Register all searchable models
        from .services import SearchService
        SearchService.register_all_models()
