"""
Trash management service.
"""
import logging
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

logger = logging.getLogger(__name__)


class TrashService:
    """
    Unified trash management service.
    
    Provides:
    - Viewing all trashed items
    - Restoring items
    - Permanent deletion
    - Automatic cleanup of expired items
    """
    
    def __init__(self, user=None):
        """
        Initialize service.
        
        Args:
            user: Current user (for permission checks)
        """
        self.user = user
    
    def get_all_trashed(self, model_filter=None, search_query=None):
        """
        Get all trashed items visible to user.
        
        Args:
            model_filter: Optional list of model names to filter
            search_query: Optional search query for title
            
        Returns:
            QuerySet of TrashRegistry entries
        """
        from ..models import TrashRegistry
        
        queryset = TrashRegistry.objects.filter(is_active=True)
        
        # Apply model filter
        if model_filter:
            queryset = queryset.filter(model_name__in=model_filter)
        
        # Apply search
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        
        # Apply user filter (non-admins only see their own)
        if self.user and not self.user.is_superuser:
            queryset = queryset.filter(trashed_by=self.user)
        
        return queryset.order_by('-created_at')
    
    def get_statistics(self):
        """
        Get trash statistics.
        
        Returns:
            dict with statistics
        """
        from ..models import TrashRegistry
        
        queryset = self.get_all_trashed()
        now = timezone.now()
        
        total = queryset.count()
        expiring_soon = queryset.filter(
            expires_at__lte=now + timedelta(days=7),
            expires_at__gt=now
        ).count()
        expired = queryset.filter(expires_at__lte=now).count()
        
        # Group by model type
        by_type = {}
        for entry in queryset.values('model_name', 'model_verbose_name').distinct():
            count = queryset.filter(model_name=entry['model_name']).count()
            by_type[entry['model_verbose_name'] or entry['model_name']] = count
        
        return {
            'total': total,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'can_restore': total - expired,
            'by_type': by_type,
        }
    
    def restore_item(self, registry_id):
        """
        Restore an item from trash.
        
        Args:
            registry_id: ID of TrashRegistry entry
            
        Returns:
            True if successful, raises exception otherwise
        """
        from ..models import TrashRegistry
        
        try:
            registry = TrashRegistry.objects.get(id=registry_id)
        except TrashRegistry.DoesNotExist:
            raise ValueError("Item not found in trash")
        
        # Check permission
        if not self._can_restore(registry):
            raise PermissionError("You don't have permission to restore this item")
        
        # Check if expired
        if registry.is_expired:
            raise ValueError("This item has expired and cannot be restored")
        
        # Restore
        success = registry.restore()
        
        if success:
            logger.info(f"Restored {registry.title} by {self.user}")
        
        return success
    
    def permanent_delete_item(self, registry_id):
        """
        Permanently delete an item.
        
        Args:
            registry_id: ID of TrashRegistry entry
            
        Returns:
            True if successful
        """
        from ..models import TrashRegistry
        
        try:
            registry = TrashRegistry.objects.get(id=registry_id)
        except TrashRegistry.DoesNotExist:
            raise ValueError("Item not found in trash")
        
        # Check permission
        if not self._can_delete(registry):
            raise PermissionError("You don't have permission to delete this item")
        
        title = registry.title
        registry.permanent_delete()
        
        logger.info(f"Permanently deleted {title} by {self.user}")
        return True
    
    def restore_multiple(self, registry_ids):
        """
        Restore multiple items.
        
        Args:
            registry_ids: List of TrashRegistry IDs
            
        Returns:
            dict with counts
        """
        restored = 0
        failed = 0
        
        for registry_id in registry_ids:
            try:
                self.restore_item(registry_id)
                restored += 1
            except Exception as e:
                logger.warning(f"Failed to restore {registry_id}: {e}")
                failed += 1
        
        return {'restored': restored, 'failed': failed}
    
    def delete_multiple(self, registry_ids):
        """
        Permanently delete multiple items.
        
        Args:
            registry_ids: List of TrashRegistry IDs
            
        Returns:
            dict with counts
        """
        deleted = 0
        failed = 0
        
        for registry_id in registry_ids:
            try:
                self.permanent_delete_item(registry_id)
                deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {registry_id}: {e}")
                failed += 1
        
        return {'deleted': deleted, 'failed': failed}
    
    def empty_expired(self):
        """
        Permanently delete all expired items.
        
        Returns:
            Number of items deleted
        """
        from ..models import TrashRegistry
        
        expired = TrashRegistry.objects.filter(
            expires_at__lte=timezone.now()
        )
        
        count = 0
        for registry in expired:
            try:
                registry.permanent_delete()
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete expired item {registry.id}: {e}")
        
        logger.info(f"Emptied {count} expired trash items")
        return count
    
    def empty_all(self, confirm=False):
        """
        Empty all trash (permanent delete everything).
        
        Args:
            confirm: Must be True to proceed
            
        Returns:
            Number of items deleted
        """
        if not confirm:
            raise ValueError("Must confirm=True to empty all trash")
        
        if not self.user or not self.user.is_superuser:
            raise PermissionError("Only admins can empty all trash")
        
        from ..models import TrashRegistry
        
        count = 0
        for registry in TrashRegistry.objects.all():
            try:
                registry.permanent_delete()
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete {registry.id}: {e}")
        
        logger.warning(f"Emptied all trash ({count} items) by {self.user}")
        return count
    
    def _can_restore(self, registry):
        """Check if user can restore this item."""
        if not self.user:
            return False
        if self.user.is_superuser:
            return True
        return registry.trashed_by == self.user
    
    def _can_delete(self, registry):
        """Check if user can permanently delete this item."""
        return self._can_restore(registry)
    
    def get_available_models(self):
        """Get list of model types in trash."""
        from ..models import TrashRegistry
        
        return list(
            TrashRegistry.objects.values(
                'model_name', 'model_verbose_name'
            ).distinct()
        )
