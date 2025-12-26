"""
Search history model for tracking user searches.
"""
from django.db import models
from django.conf import settings
from apps.core.models import SimpleBaseModel


class SearchHistoryManager(models.Manager):
    """Manager for search history."""
    
    def recent_for_user(self, user, limit=10):
        """Get recent searches for a user."""
        return self.filter(user=user).order_by('-created_at')[:limit]
    
    def popular_queries(self, days=30, limit=10):
        """Get popular search queries."""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count
        
        since = timezone.now() - timedelta(days=days)
        
        return self.filter(
            created_at__gte=since
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]


class SearchHistory(SimpleBaseModel):
    """
    User search history.
    
    Used for:
    - Showing recent searches
    - Search analytics
    - Improving search suggestions
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='search_history'
    )
    query = models.CharField(
        max_length=500,
        db_index=True,
        help_text='The search query'
    )
    results_count = models.IntegerField(
        default=0,
        help_text='Number of results returned'
    )
    
    # Filters used
    filters_used = models.JSONField(
        default=dict,
        blank=True,
        help_text='Filters applied to the search'
    )
    
    # Click tracking
    clicked_result_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID of result that was clicked'
    )
    clicked_result_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Model type of clicked result'
    )
    
    # Performance tracking
    search_duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Search execution time in milliseconds'
    )
    
    objects = SearchHistoryManager()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Search histories'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['query']),
        ]
    
    def __str__(self):
        return f'{self.user}: "{self.query}"'
    
    def record_click(self, result_id, result_type):
        """Record which result was clicked."""
        self.clicked_result_id = result_id
        self.clicked_result_type = result_type
        self.save(update_fields=['clicked_result_id', 'clicked_result_type'])
