"""
Trash views.
"""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.views import View

from apps.core.views.base import (
    BaseListView, BaseTemplateView,
    AuthenticatedAPIView, LoginRequiredMixin
)
from .models import TrashRegistry
from .services import TrashService


class TrashListView(LoginRequiredMixin, BaseListView):
    """List all trashed items."""
    
    template_name = 'trash/list.html'
    model = TrashRegistry
    paginate_by = 20
    page_title = 'Trash'
    context_object_name = 'items'
    
    def get_queryset(self):
        service = TrashService(self.request.user)
        
        model_filter = self.request.GET.getlist('type')
        search_query = self.request.GET.get('q', '')
        
        return service.get_all_trashed(
            model_filter=model_filter if model_filter else None,
            search_query=search_query if search_query else None
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = TrashService(self.request.user)
        
        context['statistics'] = service.get_statistics()
        context['available_models'] = service.get_available_models()
        context['current_filter'] = self.request.GET.getlist('type')
        context['search_query'] = self.request.GET.get('q', '')
        
        return context


class TrashDetailView(LoginRequiredMixin, BaseTemplateView):
    """View details of a trashed item."""
    
    template_name = 'trash/detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from django.shortcuts import get_object_or_404
        
        item = get_object_or_404(TrashRegistry, pk=self.kwargs['pk'])
        
        # Check permission
        if not self.request.user.is_superuser and item.trashed_by != self.request.user:
            from django.http import Http404
            raise Http404
        
        context['item'] = item
        context['original_object'] = item.get_object()
        context['page_title'] = f'Trashed: {item.title}'
        
        return context


class RestoreItemView(LoginRequiredMixin, View):
    """Restore an item from trash."""
    
    def post(self, request, pk):
        service = TrashService(request.user)
        
        try:
            service.restore_item(pk)
            messages.success(request, 'Item restored successfully.')
        except ValueError as e:
            messages.error(request, str(e))
        except PermissionError as e:
            messages.error(request, str(e))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('trash:list')


class PermanentDeleteView(LoginRequiredMixin, View):
    """Permanently delete an item."""
    
    def post(self, request, pk):
        service = TrashService(request.user)
        
        try:
            service.permanent_delete_item(pk)
            messages.success(request, 'Item permanently deleted.')
        except ValueError as e:
            messages.error(request, str(e))
        except PermissionError as e:
            messages.error(request, str(e))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('trash:list')


class RestoreMultipleView(LoginRequiredMixin, View):
    """Restore multiple items at once."""
    
    def post(self, request):
        service = TrashService(request.user)
        
        ids = request.POST.getlist('ids')
        
        if not ids:
            messages.error(request, 'No items selected.')
            return redirect('trash:list')
        
        result = service.restore_multiple(ids)
        
        if result['restored'] > 0:
            messages.success(request, f"Restored {result['restored']} items.")
        if result['failed'] > 0:
            messages.warning(request, f"Failed to restore {result['failed']} items.")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(result)
        
        return redirect('trash:list')


class DeleteMultipleView(LoginRequiredMixin, View):
    """Permanently delete multiple items at once."""
    
    def post(self, request):
        service = TrashService(request.user)
        
        ids = request.POST.getlist('ids')
        
        if not ids:
            messages.error(request, 'No items selected.')
            return redirect('trash:list')
        
        result = service.delete_multiple(ids)
        
        if result['deleted'] > 0:
            messages.success(request, f"Deleted {result['deleted']} items.")
        if result['failed'] > 0:
            messages.warning(request, f"Failed to delete {result['failed']} items.")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(result)
        
        return redirect('trash:list')


class EmptyExpiredView(LoginRequiredMixin, View):
    """Empty all expired items from trash."""
    
    def post(self, request):
        service = TrashService(request.user)
        
        count = service.empty_expired()
        
        messages.success(request, f'Deleted {count} expired items.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'count': count})
        
        return redirect('trash:list')


class EmptyAllView(LoginRequiredMixin, View):
    """Empty all trash (admin only)."""
    
    def post(self, request):
        if not request.user.is_superuser:
            messages.error(request, 'Only administrators can empty all trash.')
            return redirect('trash:list')
        
        confirm = request.POST.get('confirm') == 'true'
        
        if not confirm:
            messages.error(request, 'Please confirm this action.')
            return redirect('trash:list')
        
        service = TrashService(request.user)
        
        try:
            count = service.empty_all(confirm=True)
            messages.success(request, f'Deleted all {count} items from trash.')
        except Exception as e:
            messages.error(request, str(e))
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'count': count})
        
        return redirect('trash:list')


class TrashAPIView(AuthenticatedAPIView):
    """API endpoints for trash operations."""
    
    def get(self, request):
        """Get trash statistics and items."""
        service = TrashService(request.user)
        
        if request.GET.get('stats') == 'true':
            return self.json_success(data=service.get_statistics())
        
        # Get items
        model_filter = request.GET.getlist('type')
        limit = int(request.GET.get('limit', 20))
        
        items = service.get_all_trashed(
            model_filter=model_filter if model_filter else None
        )[:limit]
        
        return self.json_success(data={
            'items': [item.to_dict() for item in items],
            'statistics': service.get_statistics()
        })
    
    def post(self, request):
        """Handle trash actions."""
        service = TrashService(request.user)
        
        action = request.POST.get('action')
        item_id = request.POST.get('id')
        
        try:
            if action == 'restore':
                service.restore_item(item_id)
                return self.json_success('Item restored')
            
            elif action == 'delete':
                service.permanent_delete_item(item_id)
                return self.json_success('Item deleted')
            
            elif action == 'empty_expired':
                count = service.empty_expired()
                return self.json_success(f'Deleted {count} expired items')
            
            elif action == 'restore_multiple':
                ids = request.POST.getlist('ids')
                result = service.restore_multiple(ids)
                return self.json_success('Items restored', data=result)
            
            elif action == 'delete_multiple':
                ids = request.POST.getlist('ids')
                result = service.delete_multiple(ids)
                return self.json_success('Items deleted', data=result)
            
            else:
                return self.json_error('Invalid action')
                
        except ValueError as e:
            return self.json_error(str(e))
        except PermissionError as e:
            return self.json_forbidden(str(e))


class TrashWidgetView(LoginRequiredMixin, BaseTemplateView):
    """Render trash widget for sidebar/dashboard."""
    
    template_name = 'trash/partials/widget.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = TrashService(self.request.user)
        context['statistics'] = service.get_statistics()
        return context
