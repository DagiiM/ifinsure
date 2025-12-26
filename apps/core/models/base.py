"""
Base model with all critical mixins built-in.

This is the foundation for all models in the ifinsure system, providing:
- Timestamps (created_at, updated_at)
- Soft delete with trash (TrashableMixin)
- Search capabilities (SearchableMixin) 
- Notification support (NotifiableMixin)
- Visibility control (VisibilityMixin)
- GDPR/Accountability compliance (AccountabilityMixin)
"""
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class BaseModelManager(models.Manager):
    """
    Combined manager that supports:
    - Soft delete (trash) filtering
    - Visibility filtering
    - Active record filtering
    """
    
    def get_queryset(self):
        """Default queryset excludes trashed items."""
        return super().get_queryset().filter(trashed_at__isnull=True)
    
    def with_trashed(self):
        """Include trashed items in queryset."""
        return super().get_queryset()
    
    def only_trashed(self):
        """Get only trashed items."""
        return super().get_queryset().filter(trashed_at__isnull=False)
    
    def active(self):
        """Get only active (non-deleted) items."""
        return self.filter(is_active=True)
    
    def expired_trash(self):
        """Get items that have exceeded retention period."""
        return self.only_trashed().filter(
            permanent_delete_at__lte=timezone.now()
        )
    
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
            return self.filter(visibility='public', is_published=True)
        
        if user.is_superuser:
            return self.get_queryset()
        
        queryset = self.get_queryset()
        
        # Build visibility filter
        q = Q(visibility='public')  # Public items
        
        # Owner's items
        q |= Q(owner=user)
        
        # Creator's items (from AccountabilityMixin)
        q |= Q(created_by=user)
        
        # Internal items for staff
        if user.is_staff:
            q |= Q(visibility='internal')
        
        # Restricted items where user is in allowed_users
        q |= Q(visibility='restricted', allowed_users=user)
        
        # Restricted items where user's groups are in allowed_groups
        q |= Q(visibility='restricted', allowed_groups__in=user.groups.all())
        
        return queryset.filter(q).distinct()


class BaseModel(models.Model):
    """
    Abstract base model with all critical features built-in.
    
    All other models should inherit from this to get:
    
    ## Timestamps
    - `created_at`: Auto-set on creation
    - `updated_at`: Auto-set on every save
    
    ## Soft Delete (Trash)
    - `is_active`: Quick soft delete flag
    - `trashed_at`: When moved to trash
    - `trashed_by`: Who trashed it
    - `permanent_delete_at`: When to auto-delete
    - `trash()`, `restore_from_trash()`, `permanent_delete()` methods
    
    ## Visibility Control
    - `visibility`: public/private/internal/restricted
    - `owner`: Resource owner
    - `allowed_users`: M2M for restricted access
    - `allowed_groups`: M2M for group-based access
    - `is_published`: Draft/Published status
    - `is_visible_to(user)`, `can_edit(user)`, `can_delete(user)` methods
    
    ## Accountability (GDPR)
    - `created_by`: Who created this
    - `modified_by`: Who last modified
    - `consent_given`: Data processing consent
    - `is_anonymized`: Right to be forgotten
    - `retain_until`: Data retention date
    - `anonymize()`, `export_data()` methods
    
    ## Notifications
    - `notifications_enabled`: Toggle notifications
    - `watchers`: Users watching for changes
    - `notify()`, `add_watcher()` methods
    
    ## Search
    - Override `SEARCH_FIELDS`, `SEARCH_WEIGHTS` for search config
    - `search()`, `to_search_result()` class methods
    
    ## Configuration (Override in subclass)
    - `TRASH_RETENTION_DAYS = 30`: Days before permanent deletion
    - `SEARCH_FIELDS = []`: Fields to search
    - `NOTIFY_ON = ['create', 'update']`: When to notify
    - `DEFAULT_VISIBILITY = 'private'`: Default visibility
    """
    
    # ==================== TIMESTAMPS ====================
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
    
    # ==================== TRASH/SOFT DELETE ====================
    trashed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='When this item was moved to trash'
    )
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_trashed',
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
    
    # ==================== VISIBILITY ====================
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
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_owned',
        help_text='Owner of this resource'
    )
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='%(app_label)s_%(class)s_allowed',
        help_text='Users who can access this resource when restricted'
    )
    allowed_groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='%(app_label)s_%(class)s_allowed_groups',
        help_text='Groups who can access this resource when restricted'
    )
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
    
    # ==================== ACCOUNTABILITY ====================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
        help_text='User who created this record'
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_modified',
        help_text='User who last modified this record'
    )
    consent_given = models.BooleanField(
        default=False,
        help_text='Whether user consented to data processing'
    )
    consent_given_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When consent was given'
    )
    is_anonymized = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this record has been anonymized'
    )
    anonymized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this record was anonymized'
    )
    retain_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Date until which this record must be retained'
    )
    
    # ==================== NOTIFICATIONS ====================
    notifications_enabled = models.BooleanField(
        default=True,
        help_text='Whether notifications are enabled for this resource'
    )
    last_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the last notification was sent'
    )
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='%(app_label)s_%(class)s_watching',
        help_text='Users watching this resource for changes'
    )
    
    # ==================== MANAGERS ====================
    objects = BaseModelManager()
    all_objects = models.Manager()  # Bypass all filtering
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    # ==================== CONFIGURATION (Override in subclass) ====================
    
    # Trash settings
    TRASH_RETENTION_DAYS = 30
    ALLOW_PERMANENT_DELETE = True
    
    # Visibility settings
    DEFAULT_VISIBILITY = 'private'
    REQUIRE_PUBLISHED = False
    
    # Search settings (override for searchable models)
    SEARCH_FIELDS = []
    SEARCH_WEIGHTS = {}
    SEARCH_RESULT_FIELDS = ['id']
    SEARCH_TITLE_FIELD = '__str__'
    SEARCH_SUBTITLE_FIELD = None
    SEARCH_ICON = 'file'
    SEARCH_DETAIL_URL = None
    
    # Notification settings
    NOTIFY_ON = ['create', 'update', 'delete']
    NOTIFY_CHANNELS = ['in_app']
    NOTIFY_FIELDS = []
    NOTIFY_COOLDOWN = 0
    
    # GDPR settings
    GDPR_FIELDS = []
    RETENTION_DAYS = None
    
    # ==================== CORE METHODS ====================
    
    def soft_delete(self):
        """Mark record as inactive (soft delete)."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])
    
    # ==================== TRASH METHODS ====================
    
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
    
    def trash(self, user=None, reason=''):
        """Move item to trash."""
        if self.is_trashed:
            return
        
        self.trashed_at = timezone.now()
        self.trashed_by = user
        self.trash_reason = reason
        self.permanent_delete_at = timezone.now() + timedelta(days=self.TRASH_RETENTION_DAYS)
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
        self.is_active = True
        self.save()
    
    def permanent_delete(self):
        """Permanently delete item. Cannot be undone."""
        if not self.ALLOW_PERMANENT_DELETE:
            raise PermissionError(f'{self._meta.verbose_name} does not allow permanent deletion')
        super().delete()
    
    def delete(self, *args, **kwargs):
        """Override delete to trash instead of permanent delete."""
        force = kwargs.pop('force', False)
        if force:
            super().delete(*args, **kwargs)
        else:
            self.trash()
    
    @classmethod
    def empty_expired_trash(cls):
        """Permanently delete all items that have exceeded retention period."""
        expired = cls.all_objects.filter(
            trashed_at__isnull=False,
            permanent_delete_at__lte=timezone.now()
        )
        count = expired.count()
        for obj in expired:
            obj.delete(force=True)
        return count
    
    # ==================== VISIBILITY METHODS ====================
    
    def is_visible_to(self, user):
        """Check if this resource is visible to a user."""
        if self.REQUIRE_PUBLISHED and not self.is_published:
            if not user or not user.is_authenticated:
                return False
            if not user.is_superuser and self.owner != user:
                return False
        
        if self.visibility == 'public':
            return True
        
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser:
            return True
        
        if self.visibility == 'private':
            return self.owner == user or self.created_by == user
        
        if self.visibility == 'internal':
            return user.is_staff
        
        if self.visibility == 'restricted':
            if self.owner == user or self.created_by == user:
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
        return self.owner == user or self.created_by == user
    
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
    
    def publish(self):
        """Publish this resource."""
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at'])
    
    def unpublish(self):
        """Unpublish this resource."""
        self.is_published = False
        self.save(update_fields=['is_published'])
    
    # ==================== ACCOUNTABILITY METHODS ====================
    
    def record_consent(self, ip_address=None):
        """Record that consent was given for data processing."""
        self.consent_given = True
        self.consent_given_at = timezone.now()
        self.save(update_fields=['consent_given', 'consent_given_at'])
    
    def anonymize(self, user=None):
        """Anonymize PII fields (right to be forgotten)."""
        if self.is_anonymized:
            return
        
        for field_name in self.GDPR_FIELDS:
            field = self._meta.get_field(field_name)
            if isinstance(field, models.EmailField):
                setattr(self, field_name, f'anonymized_{self.pk}@deleted.local')
            elif isinstance(field, (models.CharField, models.TextField)):
                setattr(self, field_name, '[REDACTED]')
        
        self.is_anonymized = True
        self.anonymized_at = timezone.now()
        self.modified_by = user
        self.save()
    
    def export_data(self):
        """Export all data for this record (data portability)."""
        data = {}
        for field in self._meta.fields:
            value = getattr(self, field.name)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            elif hasattr(value, 'pk'):
                value = str(value.pk)
            data[field.name] = value
        return data
    
    # ==================== NOTIFICATION METHODS ====================
    
    def get_notification_recipients(self):
        """Get list of users to notify."""
        recipients = list(self.watchers.all())
        if self.created_by and self.created_by not in recipients:
            recipients.append(self.created_by)
        if self.owner and self.owner not in recipients:
            recipients.append(self.owner)
        return recipients
    
    def should_notify(self, action, changed_fields=None):
        """Check if notification should be sent."""
        if not self.notifications_enabled:
            return False
        if action not in self.NOTIFY_ON:
            return False
        if self.NOTIFY_COOLDOWN and self.last_notified_at:
            cooldown_until = self.last_notified_at + timedelta(seconds=self.NOTIFY_COOLDOWN)
            if timezone.now() < cooldown_until:
                return False
        if self.NOTIFY_FIELDS and changed_fields:
            if not any(f in self.NOTIFY_FIELDS for f in changed_fields):
                return False
        return True
    
    def add_watcher(self, user):
        """Add a user to watch this resource."""
        self.watchers.add(user)
    
    def remove_watcher(self, user):
        """Remove a user from watching this resource."""
        self.watchers.remove(user)
    
    # ==================== SEARCH METHODS ====================
    
    @classmethod
    def search(cls, query, queryset=None, limit=None):
        """Search for records matching query."""
        if queryset is None:
            queryset = cls.objects.all()
        
        if not query or not cls.SEARCH_FIELDS:
            return queryset.none() if not query else queryset
        
        q_objects = Q()
        for field in cls.SEARCH_FIELDS:
            q_objects |= Q(**{f'{field}__icontains': query})
        
        results = queryset.filter(q_objects)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_search_title(self):
        """Get display title for search results."""
        if self.SEARCH_TITLE_FIELD == '__str__':
            return str(self)
        return getattr(self, self.SEARCH_TITLE_FIELD, str(self))
    
    def get_search_subtitle(self):
        """Get subtitle/description for search results."""
        if not self.SEARCH_SUBTITLE_FIELD:
            return None
        return getattr(self, self.SEARCH_SUBTITLE_FIELD, None)
    
    def get_search_url(self):
        """Get URL for this item in search results."""
        if self.SEARCH_DETAIL_URL:
            from django.urls import reverse
            try:
                return reverse(self.SEARCH_DETAIL_URL, args=[self.pk])
            except:
                pass
        return None
    
    def to_search_result(self):
        """Convert this object to a search result dictionary."""
        return {
            'id': self.pk,
            'title': self.get_search_title(),
            'subtitle': self.get_search_subtitle(),
            'icon': self.SEARCH_ICON,
            'url': self.get_search_url(),
            'type': self._meta.verbose_name,
        }
