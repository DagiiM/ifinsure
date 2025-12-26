"""
Global search service.
"""
import logging
import time
from django.db.models import Q
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


class SearchService:
    """
    Global search service that queries across all models.
    
    Provides unified search across the entire application with:
    - Multi-model search
    - Visibility-aware filtering
    - Weighted ranking
    - Search history tracking
    """
    
    # Registry of searchable models
    _registered_models = []
    _initialized = False
    
    def __init__(self, user=None):
        """
        Initialize search service.
        
        Args:
            user: User performing the search (for visibility filtering)
        """
        self.user = user
    
    @classmethod
    def register_model(cls, model):
        """
        Register a model for global search.
        
        Args:
            model: Model class with SearchableMixin
        """
        from apps.core.mixins import SearchableMixin
        
        if hasattr(model, 'SEARCH_FIELDS') and model not in cls._registered_models:
            cls._registered_models.append(model)
            logger.debug(f"Registered model for search: {model._meta.label}")
    
    @classmethod
    def register_all_models(cls):
        """Auto-register all models with SearchableMixin."""
        if cls._initialized:
            return
        
        from apps.core.mixins import SearchableMixin
        
        for app_config in apps.get_app_configs():
            try:
                for model in app_config.get_models():
                    if hasattr(model, 'SEARCH_FIELDS') and model.SEARCH_FIELDS:
                        cls.register_model(model)
            except Exception as e:
                logger.debug(f"Could not register models from {app_config.name}: {e}")
        
        cls._initialized = True
        logger.info(f"Registered {len(cls._registered_models)} models for search")
    
    @classmethod
    def get_registered_models(cls):
        """Get list of registered model names."""
        return [
            {
                'name': model._meta.model_name,
                'verbose_name': model._meta.verbose_name.title(),
                'verbose_name_plural': model._meta.verbose_name_plural.title(),
            }
            for model in cls._registered_models
        ]
    
    def search(self, query, model_filter=None, limit=50, filters=None):
        """
        Search across all registered models.
        
        Args:
            query: Search query string
            model_filter: Optional list of model names to search
            limit: Maximum results per model
            filters: Additional filters dict
            
        Returns:
            dict with categorized results
        """
        start_time = time.time()
        
        results = {
            'query': query,
            'total': 0,
            'categories': {},
            'all': [],
        }
        
        if not query or len(query) < 2:
            return results
        
        # Try indexed search first
        indexed_results = self._search_index(query, model_filter, limit)
        if indexed_results['total'] > 0:
            results = indexed_results
        else:
            # Fall back to direct model search
            results = self._search_models(query, model_filter, limit)
        
        # Calculate search duration
        duration_ms = int((time.time() - start_time) * 1000)
        results['duration_ms'] = duration_ms
        
        # Log search
        self._log_search(query, results['total'], filters, duration_ms)
        
        return results
    
    def _search_index(self, query, model_filter=None, limit=50):
        """Search using the search index."""
        from ..models import SearchIndex
        
        results = {
            'query': query,
            'total': 0,
            'categories': {},
            'all': [],
        }
        
        index_results = SearchIndex.objects.search(
            query=query,
            user=self.user,
            model_filter=model_filter,
            limit=limit
        )
        
        for entry in index_results:
            result = entry.to_dict()
            
            # Add to category
            category = entry.model_verbose_name or entry.model_name.title()
            if category not in results['categories']:
                results['categories'][category] = []
            results['categories'][category].append(result)
            
            # Add to all
            results['all'].append(result)
            results['total'] += 1
        
        return results
    
    def _search_models(self, query, model_filter=None, limit=50):
        """Search directly in models (fallback)."""
        results = {
            'query': query,
            'total': 0,
            'categories': {},
            'all': [],
        }
        
        for model in self._registered_models:
            model_name = model._meta.model_name
            
            # Apply model filter
            if model_filter and model_name not in model_filter:
                continue
            
            try:
                # Get base queryset with visibility filtering
                queryset = model.objects.all()
                if hasattr(model.objects, 'visible_to') and self.user:
                    queryset = model.objects.visible_to(self.user)
                
                # Perform search
                if hasattr(model, 'search'):
                    model_results = model.search(query, queryset, limit=limit)
                else:
                    model_results = self._basic_search(model, query, queryset, limit)
                
                if model_results.exists():
                    category = model._meta.verbose_name_plural.title()
                    category_results = []
                    
                    for obj in model_results:
                        if hasattr(obj, 'to_search_result'):
                            result = obj.to_search_result()
                        else:
                            result = {
                                'id': obj.pk,
                                'title': str(obj),
                                'model': model_name,
                            }
                        
                        result['model'] = model_name
                        category_results.append(result)
                        results['all'].append(result)
                    
                    results['categories'][category] = category_results
                    results['total'] += len(category_results)
                    
            except Exception as e:
                logger.error(f"Error searching model {model_name}: {e}")
        
        return results
    
    def _basic_search(self, model, query, queryset, limit):
        """Basic search for models without search method."""
        search_fields = getattr(model, 'SEARCH_FIELDS', [])
        
        if not search_fields:
            return queryset.none()
        
        q_objects = Q()
        for field in search_fields:
            q_objects |= Q(**{f'{field}__icontains': query})
        
        return queryset.filter(q_objects)[:limit]
    
    def suggestions(self, query, limit=5):
        """
        Get search suggestions based on query.
        
        Args:
            query: Partial query string
            limit: Maximum suggestions to return
        """
        if not query or len(query) < 2:
            return []
        
        suggestions = set()
        
        # Get suggestions from each model
        for model in self._registered_models:
            if hasattr(model, 'search_suggestions'):
                try:
                    model_suggestions = model.search_suggestions(query, limit=3)
                    suggestions.update(model_suggestions)
                except Exception as e:
                    logger.debug(f"Error getting suggestions from {model._meta.label}: {e}")
        
        # Also get from search history
        if self.user and self.user.is_authenticated:
            from ..models import SearchHistory
            recent = SearchHistory.objects.filter(
                user=self.user,
                query__icontains=query
            ).values_list('query', flat=True)[:3]
            suggestions.update(recent)
        
        return list(suggestions)[:limit]
    
    def recent_searches(self, limit=10):
        """Get recent searches for the current user."""
        if not self.user or not self.user.is_authenticated:
            return []
        
        from ..models import SearchHistory
        return list(
            SearchHistory.objects.filter(user=self.user)
            .order_by('-created_at')
            .values('query', 'results_count', 'created_at')[:limit]
        )
    
    def _log_search(self, query, results_count, filters, duration_ms):
        """Log search to history."""
        if not self.user or not self.user.is_authenticated:
            return
        
        try:
            from ..models import SearchHistory
            SearchHistory.objects.create(
                user=self.user,
                query=query,
                results_count=results_count,
                filters_used=filters or {},
                search_duration_ms=duration_ms
            )
        except Exception as e:
            logger.warning(f"Failed to log search: {e}")
    
    def rebuild_index(self, model=None):
        """
        Rebuild the search index.
        
        Args:
            model: Optional specific model to rebuild, or all if None
        """
        from .indexer_service import IndexerService
        return IndexerService().rebuild_index(model)
