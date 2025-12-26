"""
Trashable Mixin - Soft delete with retention period.

Provides:
- Soft deletion with trash
- Configurable retention periods
- Automatic permanent deletion after retention
- Restore from trash
- Trash management utilities
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta


class TrashableManager(models.Manager):
    """Manager that excludes trashed items by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(trashed_at__isnull=True)
    
    def with_trashed(self):
        """Include trashed items in queryset."""
        return super().get_queryset()
    
    def only_trashed(self):
        """Get only trashed items."""
        return super().get_queryset().filter(trashed_at__isnull=False)
    
    def expired_trash(self):
        """Get items that have exceeded retention period."""
        return self.only_trashed().filter(
            permanent_delete_at__lte=timezone.now()
        )


class TrashableMixin(models.Model):
    """
    Mixin for soft delete with retention period before permanent deletion.
    
    Features:
    - Move items to "trash" instead of deleting
    - Configurable retention period per model
    - Automatic permanent deletion after retention expires
    - Restore from trash
    - Trash listing and management
    
    Usage:
        class Document(TrashableMixin, BaseModel):
            TRASH_RETENTION_DAYS = 30  # Keep in trash for 30 days
            
            name = models.CharField(max_length=100)
            
        # Soft delete
        document.trash()
        
        # Restore
        document.restore_from_trash()
        
        # Get trashed items
        Document.objects.only_trashed()
        
        # Include trashed in query
        Document.objects.with_trashed()
        
        # Permanently delete expired items
        Document.empty_expired_trash()
    """
    
    trashed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When this item was moved to trash'
    )
    trashed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_trashed',
        help_text='User who trashed this item'
    )
    permanent_delete_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When this item will be permanently deleted'
    )
    trash_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for trashing this item'
    )
    
    # Custom manager
    objects = TrashableManager()
    all_objects = models.Manager()  # Access all including trashed
    
    class Meta:
        abstract = True
    
    # Override in subclass - days to keep in trash before permanent deletion
    TRASH_RETENTION_DAYS = 30
    
    # Override in subclass - whether to allow permanent deletion
    ALLOW_PERMANENT_DELETE = True
    
    @property
    def is_trashed(self):
        """Check if item is in trash."""
        return self.trashed_at is not None
    
    @property
    def days_until_permanent_delete(self):
        """Get days remaining until permanent deletion."""
        if not self.permanent_delete_at:
            return None
        delta = self.permanent_delete_at - timezone.now()
        return max(0, delta.days)
    
    @property
    def time_in_trash(self):
        """Get how long item has been in trash."""
        if not self.trashed_at:
            return None
        return timezone.now() - self.trashed_at
    
    def trash(self, user=None, reason=''):
        """
        Move item to trash.
        
        Args:
            user: User who is trashing the item
            reason: Reason for trashing
        """
        if self.is_trashed:
            return
        
        self.trashed_at = timezone.now()
        self.trashed_by = user
        self.trash_reason = reason
        self.permanent_delete_at = timezone.now() + timedelta(days=self.TRASH_RETENTION_DAYS)
        
        # Also set is_active to False if using BaseModel
        if hasattr(self, 'is_active'):
            self.is_active = False
        
        self.save()
    
    def restore_from_trash(self):
        """Restore item from trash."""
        if not self.is_trashed:
            return
        
        self.trashed_at = None
        self.trashed_by = None
        self.permanent_delete_at = None
        self.trash_reason = ''
        
        # Also restore is_active if using BaseModel
        if hasattr(self, 'is_active'):
            self.is_active = True
        
        self.save()
    
    def permanent_delete(self):
        """Permanently delete item. Cannot be undone."""
        if not self.ALLOW_PERMANENT_DELETE:
            raise PermissionError(f'{self._meta.verbose_name} does not allow permanent deletion')
        
        # Call the real delete
        super().delete()
    
    def delete(self, *args, **kwargs):
        """Override delete to trash instead of permanent delete."""
        # Check if force_delete was passed
        force = kwargs.pop('force', False)
        
        if force or not self.ALLOW_PERMANENT_DELETE:
            super().delete(*args, **kwargs)
        else:
            self.trash()
    
    @classmethod
    def empty_expired_trash(cls):
        """
        Permanently delete all items that have exceeded retention period.
        Returns count of deleted items.
        """
        expired = cls.all_objects.filter(
            trashed_at__isnull=False,
            permanent_delete_at__lte=timezone.now()
        )
        count = expired.count()
        expired.delete()
        return count
    
    @classmethod
    def get_trash_statistics(cls):
        """Get statistics about trashed items."""
        trashed = cls.all_objects.filter(trashed_at__isnull=False)
        expired = trashed.filter(permanent_delete_at__lte=timezone.now())
        
        return {
            'total_trashed': trashed.count(),
            'expired': expired.count(),
            'can_restore': trashed.count() - expired.count(),
        }
    
    @classmethod
    def empty_all_trash(cls, force=False):
        """
        Permanently delete ALL trashed items regardless of retention.
        Use with caution!
        
        Args:
            force: Must be True to confirm action
        """
        if not force:
            raise ValueError('Must pass force=True to empty all trash')
        
        trashed = cls.all_objects.filter(trashed_at__isnull=False)
        count = trashed.count()
        trashed.delete()
        return count
