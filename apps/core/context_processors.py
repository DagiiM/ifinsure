"""
Context processors for global resource apps.

Provides notification count and search availability globally.
"""


def notifications_context(request):
    """
    Add notification data to template context.
    
    Returns:
        - unread_notifications_count: Number of unread notifications
        - has_notifications: Whether user has any unread notifications
    """
    context = {
        'unread_notifications_count': 0,
        'has_notifications': False,
    }
    
    if request.user.is_authenticated:
        try:
            from apps.notifications.services import NotificationService
            service = NotificationService(request.user)
            count = service.get_unread_count(request.user)
            context['unread_notifications_count'] = count
            context['has_notifications'] = count > 0
        except Exception:
            pass
    
    return context


def search_context(request):
    """
    Add search data to template context.
    
    Returns:
        - search_enabled: Whether search is available
        - search_models: List of searchable model names
    """
    context = {
        'search_enabled': True,
        'search_models': [],
    }
    
    if request.user.is_authenticated:
        try:
            from apps.search.services import SearchService
            context['search_models'] = SearchService.get_registered_models()
        except Exception:
            pass
    
    return context


def trash_context(request):
    """
    Add trash data to template context.
    
    Returns:
        - trash_count: Number of items in trash
        - trash_expiring_soon: Number of items expiring soon
    """
    context = {
        'trash_count': 0,
        'trash_expiring_soon': 0,
    }
    
    if request.user.is_authenticated:
        try:
            from apps.trash.services import TrashService
            service = TrashService(request.user)
            stats = service.get_statistics()
            context['trash_count'] = stats['total']
            context['trash_expiring_soon'] = stats['expiring_soon']
        except Exception:
            pass
    
    return context
