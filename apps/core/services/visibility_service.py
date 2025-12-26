"""
Visibility Service - Centralized access control for resources.

Provides a unified interface for checking and managing resource visibility
across all models that use VisibilityMixin.
"""
import logging
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


class VisibilityService:
    """
    Service for managing resource visibility and access control.
    
    Provides centralized methods for:
    - Checking user access to resources
    - Filtering querysets by visibility
    - Managing visibility settings
    """
    
    def __init__(self, user=None):
        """
        Initialize service with user context.
        
        Args:
            user: The user to check access for
        """
        self.user = user
    
    def can_view(self, obj):
        """
        Check if the current user can view an object.
        
        Args:
            obj: Object with VisibilityMixin
            
        Returns:
            bool: True if user can view
        """
        if not hasattr(obj, 'visibility'):
            return True  # Object doesn't use visibility
        
        return obj.is_visible_to(self.user)
    
    def can_edit(self, obj):
        """
        Check if the current user can edit an object.
        
        Args:
            obj: Object with VisibilityMixin
            
        Returns:
            bool: True if user can edit
        """
        if not hasattr(obj, 'can_edit'):
            return self.can_view(obj)
        
        return obj.can_edit(self.user)
    
    def can_delete(self, obj):
        """
        Check if the current user can delete an object.
        
        Args:
            obj: Object with VisibilityMixin
            
        Returns:
            bool: True if user can delete
        """
        if not hasattr(obj, 'can_delete'):
            return self.can_edit(obj)
        
        return obj.can_delete(self.user)
    
    def filter_visible(self, queryset):
        """
        Filter a queryset to only include visible objects.
        
        Args:
            queryset: Django queryset
            
        Returns:
            Filtered queryset
        """
        model = queryset.model
        
        # Check if model has visibility
        if not hasattr(model, 'visibility'):
            return queryset
        
        # Check if manager has visible_to method
        if hasattr(model.objects, 'visible_to'):
            return model.objects.visible_to(self.user)
        
        # Manual filtering
        return self._apply_visibility_filter(queryset)
    
    def _apply_visibility_filter(self, queryset):
        """
        Apply visibility filter manually.
        
        Args:
            queryset: Django queryset
            
        Returns:
            Filtered queryset
        """
        if not self.user:
            # Anonymous users only see public
            return queryset.filter(visibility='public', is_published=True)
        
        if self.user.is_superuser:
            # Superusers see everything
            return queryset
        
        # Build visibility query
        q = Q(visibility='public', is_published=True)
        
        if self.user.is_authenticated:
            # Owner can always see
            q |= Q(owner=self.user)
            
            # Staff can see internal
            if self.user.is_staff:
                q |= Q(visibility='internal')
            
            # Specific access
            q |= Q(allowed_users=self.user)
            
            # Group access
            user_groups = self.user.groups.all()
            if user_groups.exists():
                q |= Q(allowed_groups__in=user_groups)
        
        return queryset.filter(q).distinct()
    
    def set_visibility(self, obj, visibility, publish=None):
        """
        Set visibility on an object.
        
        Args:
            obj: Object with VisibilityMixin
            visibility: Visibility level ('public', 'private', 'internal', 'restricted')
            publish: Whether to publish (optional)
        """
        if not hasattr(obj, 'visibility'):
            raise ValueError("Object doesn't support visibility")
        
        obj.visibility = visibility
        
        if publish is not None:
            obj.is_published = publish
        
        obj.save(update_fields=['visibility', 'is_published'])
        
        logger.info(f"Set visibility of {obj} to {visibility}")
    
    def grant_access(self, obj, users=None, groups=None):
        """
        Grant access to specific users or groups.
        
        Args:
            obj: Object with VisibilityMixin
            users: List of users to grant access
            groups: List of groups to grant access
        """
        if users:
            obj.allowed_users.add(*users)
        
        if groups:
            obj.allowed_groups.add(*groups)
        
        logger.info(f"Granted access to {obj}")
    
    def revoke_access(self, obj, users=None, groups=None):
        """
        Revoke access from specific users or groups.
        
        Args:
            obj: Object with VisibilityMixin
            users: List of users to revoke access
            groups: List of groups to revoke access
        """
        if users:
            obj.allowed_users.remove(*users)
        
        if groups:
            obj.allowed_groups.remove(*groups)
        
        logger.info(f"Revoked access from {obj}")
    
    def transfer_ownership(self, obj, new_owner):
        """
        Transfer ownership of an object.
        
        Args:
            obj: Object with VisibilityMixin
            new_owner: User to transfer ownership to
        """
        if not hasattr(obj, 'owner'):
            raise ValueError("Object doesn't support ownership")
        
        old_owner = obj.owner
        obj.owner = new_owner
        obj.save(update_fields=['owner'])
        
        logger.info(f"Transferred ownership of {obj} from {old_owner} to {new_owner}")
    
    def get_accessible_content_types(self):
        """
        Get list of content types the user can access.
        
        Returns:
            List of ContentType objects
        """
        from django.apps import apps
        
        accessible = []
        
        for model in apps.get_models():
            if hasattr(model, 'visibility'):
                ct = ContentType.objects.get_for_model(model)
                accessible.append(ct)
        
        return accessible
    
    def bulk_set_visibility(self, queryset, visibility, publish=None):
        """
        Set visibility on multiple objects.
        
        Args:
            queryset: Objects to update
            visibility: Visibility level
            publish: Whether to publish (optional)
        """
        update_fields = {'visibility': visibility}
        
        if publish is not None:
            update_fields['is_published'] = publish
        
        count = queryset.update(**update_fields)
        
        logger.info(f"Updated visibility for {count} objects to {visibility}")
        
        return count
