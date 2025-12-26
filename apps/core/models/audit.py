"""
Audit log model for security and compliance.
"""
from django.db import models
from django.conf import settings
from .base import BaseModel
from .simple_base import SimpleBaseModel


class AuditLog(SimpleBaseModel):
    """
    Audit trail for security and compliance.
    Tracks all significant actions in the system.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    # timestamp replaced by created_at from BaseModel
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        user_str = self.user.email if self.user else 'System'
        return f"{user_str} - {self.action} - {self.object_repr}"
    
    @classmethod
    def log_action(cls, user, action, obj, changes=None, request=None):
        """
        Create an audit log entry.
        
        Args:
            user: The user performing the action
            action: One of the ACTION_CHOICES
            obj: The object being acted upon
            changes: Dict of changes made (optional)
            request: HTTP request for IP/user agent (optional)
        """
        if not obj:
            obj_name = 'Global'
            obj_pk = ''
            obj_repr = 'System'
        else:
            obj_name = obj.__class__.__name__
            obj_pk = str(obj.pk) if obj.pk else ''
            obj_repr = str(obj)[:255]

        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        return cls.objects.create(
            user=user,
            action=action,
            model_name=obj_name,
            object_id=obj_pk,
            object_repr=obj_repr,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
