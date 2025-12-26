"""
Simple Base Model - Lightweight version with only timestamps.

Use this for models that don't need full features like:
- Audit logs
- Settings/Configuration models
- System models (notifications, search indexes, etc.)
- M2M through tables
"""
from django.db import models


class SimpleBaseModel(models.Model):
    """
    Lightweight abstract base model with only timestamps.
    
    Use this for:
    - System/internal models
    - Configuration models
    - Audit logs themselves
    - M2M intermediary models
    
    For full-featured models (business data), use BaseModel instead.
    """
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Record creation timestamp'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Record last update timestamp'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Soft delete flag - False means deleted'
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def soft_delete(self):
        """Mark record as inactive (soft delete)."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])
