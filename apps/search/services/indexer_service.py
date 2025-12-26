"""
Indexer service for building and maintaining the search index.
"""
import logging
from django.apps import apps
from django.db import transaction

logger = logging.getLogger(__name__)


class IndexerService:
    """
    Service for building and maintaining the search index.
    
    Handles:
    - Full index rebuilds
    - Incremental updates
    - Index cleanup
    """
    
    def rebuild_index(self, model=None):
        """
        Rebuild the search index.
        
        Args:
            model: Specific model to rebuild, or all registered models if None
            
        Returns:
            dict with statistics
        """
        from ..models import SearchIndex
        from .search_service import SearchService
        
        stats = {
            'models_processed': 0,
            'objects_indexed': 0,
            'errors': 0,
        }
        
        models_to_index = [model] if model else SearchService._registered_models
        
        for model_class in models_to_index:
            try:
                count = self._index_model(model_class)
                stats['objects_indexed'] += count
                stats['models_processed'] += 1
                logger.info(f"Indexed {count} objects from {model_class._meta.label}")
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error indexing {model_class._meta.label}: {e}")
        
        return stats
    
    def _index_model(self, model_class):
        """Index all objects from a model."""
        from ..models import SearchIndex
        
        count = 0
        
        # Get all active objects
        queryset = model_class.objects.all()
        if hasattr(model_class.objects, 'filter'):
            try:
                queryset = queryset.filter(is_active=True)
            except:
                pass  # Model may not have is_active field
        
        for obj in queryset.iterator():
            try:
                SearchIndex.index_object(obj)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to index {obj}: {e}")
        
        return count
    
    def index_object(self, obj):
        """
        Index a single object.
        
        Args:
            obj: Model instance to index
        """
        from ..models import SearchIndex
        return SearchIndex.index_object(obj)
    
    def remove_object(self, obj):
        """
        Remove an object from the index.
        
        Args:
            obj: Model instance to remove
        """
        from ..models import SearchIndex
        SearchIndex.remove_object(obj)
    
    def cleanup_stale_entries(self):
        """
        Remove index entries for deleted objects.
        
        Returns:
            Number of entries removed
        """
        from ..models import SearchIndex
        from django.contrib.contenttypes.models import ContentType
        
        removed = 0
        
        for entry in SearchIndex.objects.all().iterator():
            try:
                # Check if object still exists
                model_class = entry.content_type.model_class()
                if model_class and not model_class.objects.filter(pk=entry.object_id).exists():
                    entry.delete()
                    removed += 1
            except Exception as e:
                logger.warning(f"Error checking entry {entry.id}: {e}")
        
        logger.info(f"Removed {removed} stale index entries")
        return removed
    
    def get_index_stats(self):
        """Get statistics about the search index."""
        from ..models import SearchIndex
        from django.db.models import Count
        
        total = SearchIndex.objects.count()
        
        by_model = SearchIndex.objects.values('model_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        by_visibility = SearchIndex.objects.values('visibility').annotate(
            count=Count('id')
        )
        
        return {
            'total_entries': total,
            'by_model': list(by_model),
            'by_visibility': list(by_visibility),
        }
