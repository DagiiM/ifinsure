"""
Visibility Mixin - Control access and visibility of resources.

Provides:
- Public/Private/Restricted visibility levels
- Owner-only access
- Team/Group access
- Role-based visibility
- Visibility filtering in querysets
"""
from django.db import models
from django.conf import settings


class VisibilityManager(models.Manager):
    """Manager with visibility filtering."""
    
    def visible_to(self, user):
        """
        Get items visible to a specific user.
        
        Handles:
        - Public items (visible to all)
        - Private items (visible to owner only)
        - Internal items (visible to staff)
        - Restricted items (visible to specific users/groups)
        """
        if not user or not user.is_authenticated:
            return self.filter(visibility='public')
        
        if user.is_superuser:
            return self.all()
        
        queryset = self.get_queryset()
        
        # Build visibility filter
        from django.db.models import Q
        
        q = Q(visibility='public')  # Public items
        
        # Owner's items
        if hasattr(self.model, 'owner'):
            q |= Q(owner=user)
        elif hasattr(self.model, 'created_by'):
            q |= Q(created_by=user)
        
        # Internal items for staff
        if user.is_staff:
            q |= Q(visibility='internal')
        
        # Restricted items where user is in allowed_users
        if hasattr(self.model, 'allowed_users'):
            q |= Q(visibility='restricted', allowed_users=user)
        
        # Restricted items where user's groups are in allowed_groups
        if hasattr(self.model, 'allowed_groups'):
            q |= Q(visibility='restricted', allowed_groups__in=user.groups.all())
        
        return queryset.filter(q).distinct()


class VisibilityMixin(models.Model):
    """
    Mixin for controlling resource visibility and access.
    
    Features:
    - Multiple visibility levels (public, private, internal, restricted)
    - Owner-based access
    - User whitelist for restricted items
    - Group-based access control
    - Published/Draft status
    
    Usage:
        class Document(VisibilityMixin, BaseModel):
            VISIBILITY_CHOICES = [
                ('public', 'Public'),
                ('private', 'Private'),
                ('internal', 'Internal Only'),
                ('restricted', 'Restricted'),
            ]
            DEFAULT_VISIBILITY = 'private'
            
            title = models.CharField(max_length=200)
            
        # Set visibility
        doc.visibility = 'public'
        doc.save()
        
        # Check if user can view
        if doc.is_visible_to(user):
            ...
            
        # Get all docs visible to user
        Document.objects.visible_to(user)
    """
    
    VISIBILITY_CHOICES = [
        ('public', 'Public - Visible to everyone'),
        ('private', 'Private - Visible to owner only'),
        ('internal', 'Internal - Visible to staff'),
        ('restricted', 'Restricted - Visible to specific users/groups'),
    ]
    
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private',
        db_index=True,
        help_text='Who can see this resource'
    )
    
    # Owner of the resource
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(class)s_owned',
        help_text='Owner of this resource'
    )
    
    # For restricted visibility - specific users who can access
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='%(class)s_allowed',
        help_text='Users who can access this resource when restricted'
    )
    
    # For restricted visibility - groups who can access
    allowed_groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='%(class)s_allowed',
        help_text='Groups who can access this resource when restricted'
    )
    
    # Published status (draft items may be hidden)
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this resource is published'
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this resource was published'
    )
    
    # Custom manager
    objects = VisibilityManager()
    
    class Meta:
        abstract = True
    
    # Override in subclass
    DEFAULT_VISIBILITY = 'private'
    
    # Override - whether unpublished items should be hidden
    REQUIRE_PUBLISHED = False
    
    def is_visible_to(self, user):
        """
        Check if this resource is visible to a user.
        
        Args:
            user: User to check visibility for
            
        Returns:
            bool: True if user can see this resource
        """
        # Check published status if required
        if self.REQUIRE_PUBLISHED and not self.is_published:
            if not user or not user.is_authenticated:
                return False
            if not user.is_superuser and self.owner != user:
                return False
        
        # Public items visible to all
        if self.visibility == 'public':
            return True
        
        # Must be authenticated for other visibility levels
        if not user or not user.is_authenticated:
            return False
        
        # Superusers see everything
        if user.is_superuser:
            return True
        
        # Private - owner only
        if self.visibility == 'private':
            return self.owner == user
        
        # Internal - staff only
        if self.visibility == 'internal':
            return user.is_staff
        
        # Restricted - check allowed users and groups
        if self.visibility == 'restricted':
            if self.owner == user:
                return True
            if self.allowed_users.filter(pk=user.pk).exists():
                return True
            if self.allowed_groups.filter(pk__in=user.groups.values_list('pk')).exists():
                return True
            return False
        
        return False
    
    def can_edit(self, user):
        """Check if user can edit this resource."""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.owner == user
    
    def can_delete(self, user):
        """Check if user can delete this resource."""
        return self.can_edit(user)
    
    def make_public(self):
        """Make this resource public."""
        self.visibility = 'public'
        self.save(update_fields=['visibility'])
    
    def make_private(self):
        """Make this resource private."""
        self.visibility = 'private'
        self.save(update_fields=['visibility'])
    
    def make_internal(self):
        """Make this resource internal (staff only)."""
        self.visibility = 'internal'
        self.save(update_fields=['visibility'])
    
    def make_restricted(self, users=None, groups=None):
        """
        Make this resource restricted to specific users/groups.
        
        Args:
            users: List of User instances or IDs
            groups: List of Group instances or IDs
        """
        self.visibility = 'restricted'
        self.save(update_fields=['visibility'])
        
        if users:
            self.allowed_users.set(users)
        if groups:
            self.allowed_groups.set(groups)
    
    def publish(self):
        """Publish this resource."""
        from django.utils import timezone
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at'])
    
    def unpublish(self):
        """Unpublish this resource."""
        self.is_published = False
        self.save(update_fields=['is_published'])
    
    def grant_access(self, user):
        """Grant access to a specific user."""
        self.allowed_users.add(user)
    
    def revoke_access(self, user):
        """Revoke access from a specific user."""
        self.allowed_users.remove(user)
    
    def grant_group_access(self, group):
        """Grant access to a group."""
        self.allowed_groups.add(group)
    
    def revoke_group_access(self, group):
        """Revoke access from a group."""
        self.allowed_groups.remove(group)
