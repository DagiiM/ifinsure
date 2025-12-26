"""
Base Service - Common functionality for all service classes.

Provides:
- Standardized error handling
- Audit logging integration
- Transaction management
- Common CRUD operations
- Query optimization helpers
"""
from functools import wraps
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError, PermissionDenied
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


class ServiceException(Exception):
    """Base exception for service layer errors."""
    
    def __init__(self, message, code=None, details=None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(ServiceException):
    """Raised when a resource is not found."""
    pass


class PermissionError(ServiceException):
    """Raised when user doesn't have permission."""
    pass


class ValidationError(ServiceException):
    """Raised when validation fails."""
    pass


def service_action(audit=True, atomic=True):
    """
    Decorator for service methods that provides:
    - Automatic transaction management
    - Error handling and logging
    - Optional audit logging
    
    Usage:
        class UserService(BaseService):
            @service_action(audit=True)
            def create_user(self, email, password, **kwargs):
                ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get user for audit if available
            user = kwargs.pop('_user', None) or getattr(self, '_current_user', None)
            
            try:
                if atomic:
                    with transaction.atomic():
                        result = func(self, *args, **kwargs)
                else:
                    result = func(self, *args, **kwargs)
                
                # Audit logging
                if audit and user:
                    self._log_action(
                        action=func.__name__,
                        user=user,
                        success=True,
                        details={'args_count': len(args), 'kwargs_keys': list(kwargs.keys())}
                    )
                
                return result
                
            except Exception as e:
                # Log error
                logger.error(f'{self.__class__.__name__}.{func.__name__} failed: {e}')
                
                if audit and user:
                    self._log_action(
                        action=func.__name__,
                        user=user,
                        success=False,
                        details={'error': str(e)}
                    )
                
                raise
        
        return wrapper
    return decorator


class BaseService:
    """
    Base class for all service classes.
    
    Features:
    - Standardized CRUD operations
    - Error handling with custom exceptions
    - Audit logging integration
    - Query optimization helpers
    - Pagination support
    
    Usage:
        class UserService(BaseService):
            model = User
            
            def create_user(self, email, password, **kwargs):
                user = self.create(email=email, **kwargs)
                user.set_password(password)
                user.save()
                return user
    """
    
    # Override in subclass - the model this service operates on
    model = None
    
    # Override - default ordering for lists
    default_ordering = ['-created_at']
    
    # Override - fields to select_related by default
    select_related = []
    
    # Override - fields to prefetch_related by default
    prefetch_related = []
    
    def __init__(self, user=None):
        """
        Initialize service with optional user context.
        
        Args:
            user: User performing the operations (for audit)
        """
        self._current_user = user
    
    def with_user(self, user):
        """Set current user context."""
        self._current_user = user
        return self
    
    # ==================== Query Methods ====================
    
    def get_queryset(self):
        """Get base queryset with optimizations."""
        qs = self.model.objects.all()
        
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)
        
        return qs
    
    def get(self, pk):
        """
        Get single object by primary key.
        
        Args:
            pk: Primary key
            
        Returns:
            Model instance
            
        Raises:
            NotFoundError: If not found
        """
        try:
            return self.get_queryset().get(pk=pk)
        except ObjectDoesNotExist:
            raise NotFoundError(f'{self.model._meta.verbose_name} not found', code='not_found')
    
    def get_or_none(self, **kwargs):
        """Get object or return None if not found."""
        try:
            return self.get_queryset().get(**kwargs)
        except ObjectDoesNotExist:
            return None
    
    def get_or_404(self, **kwargs):
        """Get object or raise Http404."""
        try:
            return self.get_queryset().get(**kwargs)
        except ObjectDoesNotExist:
            raise Http404(f'{self.model._meta.verbose_name} not found')
    
    def filter(self, **kwargs):
        """Filter queryset."""
        return self.get_queryset().filter(**kwargs)
    
    def list(self, filters=None, ordering=None, limit=None, offset=None):
        """
        Get list of objects with optional filtering and pagination.
        
        Args:
            filters: Dict of filter kwargs
            ordering: List of ordering fields
            limit: Max results
            offset: Skip first N results
            
        Returns:
            QuerySet
        """
        qs = self.get_queryset()
        
        if filters:
            qs = qs.filter(**filters)
        
        qs = qs.order_by(*(ordering or self.default_ordering))
        
        if offset:
            qs = qs[offset:]
        if limit:
            qs = qs[:limit]
        
        return qs
    
    def paginate(self, queryset=None, page=1, per_page=20):
        """
        Paginate queryset.
        
        Args:
            queryset: QuerySet to paginate (default: get_queryset())
            page: Page number (1-indexed)
            per_page: Items per page
            
        Returns:
            dict with items, page, per_page, total, pages
        """
        from django.core.paginator import Paginator, EmptyPage
        
        qs = queryset if queryset is not None else self.get_queryset()
        paginator = Paginator(qs, per_page)
        
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        return {
            'items': list(page_obj.object_list),
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_prev': page_obj.has_previous(),
        }
    
    def exists(self, **kwargs):
        """Check if object matching criteria exists."""
        return self.get_queryset().filter(**kwargs).exists()
    
    def count(self, **kwargs):
        """Count objects matching criteria."""
        qs = self.get_queryset()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.count()
    
    # ==================== CRUD Methods ====================
    
    @transaction.atomic
    def create(self, **kwargs):
        """
        Create new object.
        
        Args:
            **kwargs: Model field values
            
        Returns:
            Created model instance
        """
        # Set created_by if model has it and user is set
        if hasattr(self.model, 'created_by') and self._current_user:
            kwargs.setdefault('created_by', self._current_user)
        
        instance = self.model(**kwargs)
        instance.full_clean()
        instance.save()
        
        self._log_action('create', instance=instance)
        
        return instance
    
    @transaction.atomic
    def update(self, instance, **kwargs):
        """
        Update object.
        
        Args:
            instance: Model instance to update
            **kwargs: Fields to update
            
        Returns:
            Updated model instance
        """
        # Track changes for audit
        changes = {}
        for field, value in kwargs.items():
            old_value = getattr(instance, field, None)
            if old_value != value:
                changes[field] = {'from': old_value, 'to': value}
                setattr(instance, field, value)
        
        # Set modified_by if model has it
        if hasattr(instance, 'modified_by') and self._current_user:
            instance.modified_by = self._current_user
        
        if changes:
            instance.full_clean()
            instance.save()
            self._log_action('update', instance=instance, details={'changes': changes})
        
        return instance
    
    @transaction.atomic
    def delete(self, instance, soft=True):
        """
        Delete object.
        
        Args:
            instance: Model instance to delete
            soft: If True and model has soft_delete, use it
            
        Returns:
            bool
        """
        if soft and hasattr(instance, 'soft_delete'):
            instance.soft_delete()
        elif soft and hasattr(instance, 'trash'):
            instance.trash(user=self._current_user)
        else:
            instance.delete()
        
        self._log_action('delete', instance=instance)
        return True
    
    @transaction.atomic
    def bulk_create(self, objects_data):
        """
        Bulk create objects.
        
        Args:
            objects_data: List of dicts with field values
            
        Returns:
            List of created instances
        """
        instances = [self.model(**data) for data in objects_data]
        created = self.model.objects.bulk_create(instances)
        
        self._log_action('bulk_create', details={'count': len(created)})
        return created
    
    @transaction.atomic
    def bulk_update(self, instances, fields):
        """
        Bulk update objects.
        
        Args:
            instances: List of model instances
            fields: List of field names to update
            
        Returns:
            Number of updated rows
        """
        count = self.model.objects.bulk_update(instances, fields)
        self._log_action('bulk_update', details={'count': count, 'fields': fields})
        return count
    
    # ==================== Audit Methods ====================
    
    def _log_action(self, action, instance=None, user=None, success=True, details=None, changes=None):
        """Log action to audit log. Supports both 'details' and 'changes' for compatibility."""
        try:
            from apps.core.models import AuditLog
            
            log_user = user or self._current_user
            if not log_user:
                return
            
            log_changes = changes or details
            
            AuditLog.log_action(
                user=log_user,
                action=action.upper(),
                obj=instance,
                changes=log_changes
            )
        except Exception as e:
            logger.warning(f'Failed to log audit: {e}')
    
    # ==================== Utility Methods ====================
    
    def validate(self, instance):
        """Validate instance."""
        try:
            instance.full_clean()
            return True
        except Exception:
            return False
    
    def get_statistics(self):
        """
        Get basic statistics for this model.
        Override in subclass for custom stats.
        """
        qs = self.get_queryset()
        
        stats = {
            'total': qs.count(),
        }
        
        # Add is_active counts if model has it
        if hasattr(self.model, 'is_active'):
            stats['active'] = qs.filter(is_active=True).count()
            stats['inactive'] = stats['total'] - stats['active']
        
        return stats
