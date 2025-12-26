"""
Search index model for caching searchable content.
"""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.core.models import SimpleBaseModel


class SearchIndexManager(models.Manager):
    """Manager for search index operations."""
    
    def search(self, query, user=None, model_filter=None, limit=50):
        """
        Search the index.
        
        Args:
            query: Search query string
            user: User performing search (for visibility filtering)
            model_filter: List of model names to filter by
            limit: Maximum results
        """
        from django.db.models import Q
        
        if not query or len(query) < 2:
            return self.none()
        
        queryset = self.filter(is_active=True)
        
        # Apply model filter
        if model_filter:
            queryset = queryset.filter(model_name__in=model_filter)
        
        # Apply visibility filter
        if user:
            if user.is_superuser:
                pass  # No filter needed
            elif user.is_authenticated:
                queryset = queryset.filter(
                    Q(visibility='public') |
                    Q(owner_id=user.id) |
                    (Q(visibility='internal') & Q(owner_id__isnull=True))
                )
            else:
                queryset = queryset.filter(visibility='public')
        else:
            queryset = queryset.filter(visibility='public')
        
        # Search in title, subtitle, and content
        search_query = Q(title__icontains=query) | \
                      Q(subtitle__icontains=query) | \
                      Q(content__icontains=query) | \
                      Q(keywords__icontains=query)
        
        queryset = queryset.filter(search_query)
        
        # Order by weight and title match
        queryset = queryset.order_by('-weight', 'title')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    def rebuild_index(self, model=None):
        """
        Rebuild the search index.
        
        Args:
            model: Optional specific model to rebuild
        """
        from .search_service import SearchService
        return SearchService().rebuild_index(model)


class SearchIndex(SimpleBaseModel):
    """
    Cached search index for fast lookups.
    
    Stores denormalized searchable content from various models
    for efficient global search.
    """
    
    # Link to the actual object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        db_index=True
    )
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Indexed content
    title = models.CharField(
        max_length=500,
        db_index=True,
        help_text='Primary searchable title'
    )
    subtitle = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Secondary text (description, summary)'
    )
    content = models.TextField(
        blank=True,
        default='',
        help_text='Full text content for search'
    )
    keywords = models.TextField(
        blank=True,
        default='',
        help_text='Additional keywords for search'
    )
    
    # Metadata for display
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
    icon = models.CharField(
        max_length=50,
        default='file',
        help_text='Icon for display in search results'
    )
    url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL to the object'
    )
    
    # Visibility (denormalized for performance)
    visibility = models.CharField(
        max_length=20,
        default='private',
        db_index=True,
        help_text='Visibility level from source object'
    )
    owner_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Owner user ID for access control'
    )
    
    # Search ranking
    weight = models.IntegerField(
        default=1,
        db_index=True,
        help_text='Weight for ranking (higher = more relevant)'
    )
    
    # Extra data
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional data for display'
    )
    
    objects = SearchIndexManager()
    
    class Meta:
        unique_together = ['content_type', 'object_id']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['model_name', 'visibility']),
            models.Index(fields=['owner_id', 'visibility']),
        ]
        verbose_name = 'Search Index Entry'
        verbose_name_plural = 'Search Index Entries'
    
    def __str__(self):
        return f"{self.model_name}: {self.title}"
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            'id': self.pk,
            'object_id': self.object_id,
            'title': self.title,
            'subtitle': self.subtitle,
            'model': self.model_name,
            'model_verbose_name': self.model_verbose_name,
            'icon': self.icon,
            'url': self.url,
            'weight': self.weight,
            'extra': self.extra_data,
        }
    
    @classmethod
    def index_object(cls, obj):
        """
        Index a single object.
        
        Args:
            obj: Model instance to index (must have SearchableMixin)
        """
        from apps.core.mixins import SearchableMixin
        
        if not isinstance(obj, SearchableMixin):
            return None
        
        content_type = ContentType.objects.get_for_model(obj)
        
        # Get or create index entry
        index_entry, created = cls.objects.update_or_create(
            content_type=content_type,
            object_id=obj.pk,
            defaults={
                'title': obj.get_search_title(),
                'subtitle': obj.get_search_subtitle() or '',
                'content': cls._get_searchable_content(obj),
                'model_name': obj._meta.model_name,
                'model_verbose_name': obj._meta.verbose_name.title(),
                'icon': getattr(obj, 'SEARCH_ICON', 'file'),
                'url': obj.get_search_url() or '',
                'visibility': getattr(obj, 'visibility', 'private'),
                'owner_id': getattr(obj, 'owner_id', None) or getattr(obj, 'created_by_id', None),
                'weight': cls._calculate_weight(obj),
            }
        )
        
        return index_entry
    
    @classmethod
    def remove_object(cls, obj):
        """Remove an object from the index."""
        content_type = ContentType.objects.get_for_model(obj)
        cls.objects.filter(
            content_type=content_type,
            object_id=obj.pk
        ).delete()
    
    @classmethod
    def _get_searchable_content(cls, obj):
        """Extract searchable content from object."""
        content_parts = []
        
        for field in obj.get_search_fields():
            value = getattr(obj, field, None)
            if value:
                content_parts.append(str(value))
        
        return ' '.join(content_parts)
    
    @classmethod
    def _calculate_weight(cls, obj):
        """Calculate search weight for object."""
        weight = 1
        
        # Increase weight for recently updated items
        if hasattr(obj, 'updated_at'):
            from django.utils import timezone
            from datetime import timedelta
            
            if obj.updated_at > timezone.now() - timedelta(days=7):
                weight += 2
            elif obj.updated_at > timezone.now() - timedelta(days=30):
                weight += 1
        
        # Use model-defined weight if available
        if hasattr(obj, 'SEARCH_WEIGHT'):
            weight = obj.SEARCH_WEIGHT
        
        return weight
