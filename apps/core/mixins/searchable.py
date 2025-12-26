"""
Searchable Mixin - Granular search capabilities at model level.

Provides:
- Configurable search fields
- Weighted search results
- Custom result field selection
- Full-text search support
- Search indexing helpers
"""
from django.db import models
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat


class SearchableMixin(models.Model):
    """
    Mixin for granular search capabilities at model level.
    
    Features:
    - Define which fields are searchable
    - Configure search result display fields
    - Support weighted search (some fields more important)
    - Full-text search with ranking
    - Search suggestions/autocomplete
    
    Usage:
        class Customer(SearchableMixin, BaseModel):
            # Fields to search in
            SEARCH_FIELDS = ['first_name', 'last_name', 'email', 'phone']
            
            # Weighted fields (higher = more relevant)
            SEARCH_WEIGHTS = {
                'email': 3,
                'phone': 2,
                'first_name': 1,
                'last_name': 1,
            }
            
            # Fields to return in search results
            SEARCH_RESULT_FIELDS = ['id', 'first_name', 'last_name', 'email']
            
            # Field to use as display title in results
            SEARCH_TITLE_FIELD = 'full_name'
            
            # Field to use as subtitle/description
            SEARCH_SUBTITLE_FIELD = 'email'
            
            first_name = models.CharField(max_length=100)
            last_name = models.CharField(max_length=100)
            email = models.EmailField()
    """
    
    class Meta:
        abstract = True
    
    # Override in subclass - fields to search
    SEARCH_FIELDS = []
    
    # Override in subclass - field weights for ranking (higher = more important)
    SEARCH_WEIGHTS = {}
    
    # Override in subclass - fields to include in search results
    SEARCH_RESULT_FIELDS = ['id']
    
    # Override in subclass - field or property for result title
    SEARCH_TITLE_FIELD = '__str__'
    
    # Override in subclass - field or property for result subtitle
    SEARCH_SUBTITLE_FIELD = None
    
    # Override in subclass - model icon for search results
    SEARCH_ICON = 'file'
    
    # Override in subclass - URL pattern name for detail view
    SEARCH_DETAIL_URL = None
    
    @classmethod
    def get_search_fields(cls):
        """Get fields to search in."""
        return cls.SEARCH_FIELDS or []
    
    @classmethod
    def get_search_result_fields(cls):
        """Get fields to include in search results."""
        return cls.SEARCH_RESULT_FIELDS
    
    @classmethod
    def search(cls, query, queryset=None, limit=None):
        """
        Search for records matching query.
        
        Args:
            query: Search query string
            queryset: Optional base queryset to filter
            limit: Maximum results to return
            
        Returns:
            QuerySet of matching records
        """
        if queryset is None:
            queryset = cls.objects.all()
        
        if not query or not cls.SEARCH_FIELDS:
            return queryset.none() if not query else queryset
        
        # Build Q objects for each search field
        q_objects = Q()
        for field in cls.SEARCH_FIELDS:
            q_objects |= Q(**{f'{field}__icontains': query})
        
        results = queryset.filter(q_objects)
        
        if limit:
            results = results[:limit]
        
        return results
    
    @classmethod
    def weighted_search(cls, query, queryset=None, limit=None):
        """
        Search with weighted ranking based on SEARCH_WEIGHTS.
        Returns list of (object, score) tuples sorted by score.
        """
        results = cls.search(query, queryset, limit=None)
        
        scored_results = []
        query_lower = query.lower()
        
        for obj in results:
            score = 0
            for field, weight in cls.SEARCH_WEIGHTS.items():
                value = getattr(obj, field, None)
                if value and query_lower in str(value).lower():
                    # Exact match gets higher score
                    if str(value).lower() == query_lower:
                        score += weight * 3
                    # Starts with query gets medium score
                    elif str(value).lower().startswith(query_lower):
                        score += weight * 2
                    # Contains query gets base score
                    else:
                        score += weight
            
            if score > 0:
                scored_results.append((obj, score))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        if limit:
            scored_results = scored_results[:limit]
        
        return scored_results
    
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
        """
        Convert this object to a search result dictionary.
        Returns all fields specified in SEARCH_RESULT_FIELDS plus metadata.
        """
        result = {
            'id': self.pk,
            'title': self.get_search_title(),
            'subtitle': self.get_search_subtitle(),
            'icon': self.SEARCH_ICON,
            'url': self.get_search_url(),
            'type': self._meta.verbose_name,
        }
        
        # Add configured result fields
        for field in self.SEARCH_RESULT_FIELDS:
            if field not in result:
                value = getattr(self, field, None)
                # Handle datetime serialization
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif hasattr(value, 'pk'):
                    value = str(value)
                result[field] = value
        
        return result
    
    @classmethod
    def search_suggestions(cls, query, limit=5):
        """
        Get search suggestions/autocomplete for query.
        Returns list of suggestion strings.
        """
        if not query or len(query) < 2:
            return []
        
        suggestions = set()
        results = cls.search(query, limit=limit * 2)
        
        for obj in results:
            # Add title as suggestion
            title = obj.get_search_title()
            if title and query.lower() in title.lower():
                suggestions.add(title)
            
            # Add matched field values as suggestions
            for field in cls.SEARCH_FIELDS:
                value = getattr(obj, field, None)
                if value and query.lower() in str(value).lower():
                    suggestions.add(str(value))
        
        return list(suggestions)[:limit]
