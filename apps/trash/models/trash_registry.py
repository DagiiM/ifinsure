"""
Trash registry model for tracking all trashed items.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from datetime import timedelta
from apps.core.models import SimpleBaseModel


class TrashRegistryManager(models.Manager):
    """Manager for trash registry."""
    
    def for_user(self, user):
        """Get trashed items for a specific user."""
        if user.is_superuser:
            return self.all()
        return self.filter(trashed_by=user)
    
    def expiring_soon(self, days=7):
        """Get items expiring within specified days."""
        threshold = timezone.now() + timedelta(days=days)
        return self.filter(expires_at__lte=threshold, expires_at__gt=timezone.now())
    
    def expired(self):
        """Get expired items."""
        return self.filter(expires_at__lte=timezone.now())


class TrashRegistry(SimpleBaseModel):
    """
    Central registry of all trashed items across all models.
    
    Provides unified trash view and management across the application.
    When an object is trashed using TrashableMixin, an entry is created here
    to enable cross-model trash management.
    """
    
    # Link to the actual trashed object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        db_index=True
    )
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Cached data for display (so we can show info even if object is gone)
    title = models.CharField(
        max_length=500,
        help_text='Display title of the trashed item'
    )
    subtitle = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Additional info about the item'
    )
    icon = models.CharField(
        max_length=50,
        default='file',
        help_text='Icon for display'
    )
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Name of the source model'
    )
    model_verbose_name = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )
    
    # Trash metadata
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trashed_items',
        help_text='User who trashed this item'
    )
    trash_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for trashing'
    )
    
    # Original data backup (for restoration if needed)
    original_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Backup of important data before trashing'
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        db_index=True,
        help_text='When this item will be permanently deleted'
    )
    
    # Restore URL (cached)
    restore_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL for restoring this item'
    )
    
    objects = TrashRegistryManager()
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['content_type', 'object_id']
        verbose_name = 'Trash Item'
        verbose_name_plural = 'Trash Items'
        indexes = [
            models.Index(fields=['trashed_by', 'created_at']),
            models.Index(fields=['model_name']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Trashed: {self.title}"
    
    @property
    def days_until_expiry(self):
        """Get days remaining until permanent deletion."""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    @property
    def is_expired(self):
        """Check if item has expired."""
        return self.expires_at and self.expires_at <= timezone.now()
    
    @property
    def time_in_trash(self):
        """Get how long item has been in trash."""
        delta = timezone.now() - self.created_at
        
        if delta.days > 0:
            return f"{delta.days} days"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} hours"
        else:
            return f"{delta.seconds // 60} minutes"
    
    def get_object(self):
        """
        Get the actual trashed object.
        
        Returns None if object no longer exists.
        """
        model_class = self.content_type.model_class()
        if not model_class:
            return None
        
        try:
            # Try to get from all_objects manager (includes trashed)
            if hasattr(model_class, 'all_objects'):
                return model_class.all_objects.get(pk=self.object_id)
            return model_class.objects.get(pk=self.object_id)
        except model_class.DoesNotExist:
            return None
    
    def restore(self):
        """
        Restore the object from trash.
        
        Returns True if successful, False otherwise.
        """
        obj = self.get_object()
        
        if obj is None:
            return False
        
        # Restore using object's method if available
        if hasattr(obj, 'restore_from_trash'):
            obj.restore_from_trash()
        elif hasattr(obj, 'restore'):
            obj.restore()
        else:
            # Fallback: just set is_active to True
            if hasattr(obj, 'is_active'):
                obj.is_active = True
                obj.save(update_fields=['is_active'])
            
            if hasattr(obj, 'trashed_at'):
                obj.trashed_at = None
                obj.trashed_by = None
                obj.permanent_delete_at = None
                obj.save()
        
        # Remove from registry
        self.delete()
        return True
    
    def permanent_delete(self):
        """
        Permanently delete the object.
        
        This cannot be undone.
        """
        obj = self.get_object()
        
        if obj:
            # Use force delete to bypass soft delete
            if hasattr(obj, 'delete'):
                try:
                    obj.delete(force=True)
                except TypeError:
                    # delete() doesn't accept force parameter
                    obj.delete()
        
        # Remove from registry
        self.delete()
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            'id': self.pk,
            'object_id': self.object_id,
            'title': self.title,
            'subtitle': self.subtitle,
            'icon': self.icon,
            'model': self.model_name,
            'model_verbose_name': self.model_verbose_name,
            'trashed_by': str(self.trashed_by) if self.trashed_by else None,
            'trash_reason': self.trash_reason,
            'time_in_trash': self.time_in_trash,
            'days_until_expiry': self.days_until_expiry,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @classmethod
    def register_trashed_object(cls, obj, user=None, reason=''):
        """
        Register an object in the trash registry.
        
        Args:
            obj: The object being trashed
            user: User who trashed it
            reason: Reason for trashing
        """
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(obj)
        
        # Get display info
        title = str(obj)
        if hasattr(obj, 'get_search_title'):
            title = obj.get_search_title()
        
        subtitle = ''
        if hasattr(obj, 'get_search_subtitle'):
            subtitle = obj.get_search_subtitle() or ''
        
        icon = getattr(obj, 'SEARCH_ICON', 'file')
        
        # Calculate expiry
        retention_days = getattr(obj, 'TRASH_RETENTION_DAYS', 30)
        expires_at = timezone.now() + timedelta(days=retention_days)
        
        # Create or update registry entry
        entry, created = cls.objects.update_or_create(
            content_type=content_type,
            object_id=obj.pk,
            defaults={
                'title': title[:500],
                'subtitle': subtitle[:500],
                'icon': icon,
                'model_name': obj._meta.model_name,
                'model_verbose_name': obj._meta.verbose_name.title(),
                'trashed_by': user,
                'trash_reason': reason,
                'expires_at': expires_at,
            }
        )
        
        return entry
    
    @classmethod
    def unregister_object(cls, obj):
        """Remove an object from the trash registry."""
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(obj)
        cls.objects.filter(
            content_type=content_type,
            object_id=obj.pk
        ).delete()
