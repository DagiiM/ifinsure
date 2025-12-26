"""
Search views.
"""
from django.http import JsonResponse
from django.views import View

from apps.core.views.base import (
    BaseTemplateView, AuthenticatedAPIView, 
    LoginRequiredMixin, BaseContextMixin
)
from .services import SearchService


class GlobalSearchView(LoginRequiredMixin, BaseTemplateView):
    """Global search page."""
    
    template_name = 'search/global.html'
    page_title = 'Search'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        model_filter = self.request.GET.getlist('type')
        
        context['query'] = query
        context['model_filter'] = model_filter
        context['available_models'] = SearchService.get_registered_models()
        
        if query:
            service = SearchService(self.request.user)
            context['results'] = service.search(
                query=query,
                model_filter=model_filter if model_filter else None
            )
        
        return context


class SearchAPIView(AuthenticatedAPIView):
    """Search API endpoint for AJAX requests."""
    
    def get(self, request):
        """Perform search and return JSON results."""
        query = request.GET.get('q', '')
        model_filter = request.GET.getlist('type')
        limit = int(request.GET.get('limit', 20))
        
        service = SearchService(request.user)
        
        # Handle suggestions request
        if request.GET.get('suggestions') == 'true':
            suggestions = service.suggestions(query)
            return self.json_success(data={'suggestions': suggestions})
        
        # Handle recent searches request
        if request.GET.get('recent') == 'true':
            recent = service.recent_searches()
            return self.json_success(data={'recent': recent})
        
        # Perform search
        results = service.search(
            query=query,
            model_filter=model_filter if model_filter else None,
            limit=limit
        )
        
        return self.json_success(data=results)


class SuggestionsView(AuthenticatedAPIView):
    """API endpoint for search suggestions/autocomplete."""
    
    def get(self, request):
        query = request.GET.get('q', '')
        limit = int(request.GET.get('limit', 5))
        
        service = SearchService(request.user)
        suggestions = service.suggestions(query, limit=limit)
        
        return self.json_success(data={'suggestions': suggestions})


class RecentSearchesView(AuthenticatedAPIView):
    """API endpoint for recent searches."""
    
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        
        service = SearchService(request.user)
        recent = service.recent_searches(limit=limit)
        
        return self.json_success(data={'recent': recent})


class SearchRecordClickView(AuthenticatedAPIView):
    """Record when a search result is clicked."""
    
    def post(self, request):
        from .models import SearchHistory
        
        history_id = request.POST.get('history_id')
        result_id = request.POST.get('result_id')
        result_type = request.POST.get('result_type')
        
        try:
            history = SearchHistory.objects.get(
                id=history_id,
                user=request.user
            )
            history.record_click(result_id, result_type)
            return self.json_success('Click recorded')
        except SearchHistory.DoesNotExist:
            return self.json_not_found()


class SearchModalView(LoginRequiredMixin, BaseTemplateView):
    """Render search modal content (for AJAX loading)."""
    
    template_name = 'search/partials/search_modal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_models'] = SearchService.get_registered_models()
        
        service = SearchService(self.request.user)
        context['recent_searches'] = service.recent_searches(limit=5)
        
        return context


class RebuildIndexView(AuthenticatedAPIView):
    """Admin endpoint to rebuild search index."""
    
    def post(self, request):
        # Check admin permission
        if not request.user.is_superuser:
            return self.json_forbidden('Admin access required')
        
        from .services import IndexerService
        
        model_name = request.POST.get('model')
        
        indexer = IndexerService()
        
        if model_name:
            # Rebuild specific model
            from django.apps import apps
            try:
                model = apps.get_model(model_name)
                stats = indexer.rebuild_index(model)
            except LookupError:
                return self.json_error(f'Model not found: {model_name}')
        else:
            # Rebuild all
            stats = indexer.rebuild_index()
        
        return self.json_success('Index rebuilt', data=stats)
