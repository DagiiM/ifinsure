"""
URL configuration for ifinsure project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Docker/load balancer health probes."""
    return JsonResponse({'status': 'healthy', 'service': 'ifinsure'})

# Admin site customization
admin.site.site_header = 'ifinsure Administration'
admin.site.site_title = 'ifinsure Admin'
admin.site.index_title = 'Administration Dashboard'

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('', include('apps.core.urls')),  # Reviews, sitemap
    path('accounts/', include('apps.accounts.urls')),
    path('crm/', include('apps.crm.urls')),
    path('policies/', include('apps.policies.urls')),
    path('claims/', include('apps.claims.urls')),
    path('billing/', include('apps.billing.urls')),
    path('wallet/', include('apps.wallets.urls')),
    path('workflow/', include('apps.workflow.urls')),
    path('integrations/', include('apps.integrations.urls')),
    # Global resource apps
    path('notifications/', include('apps.notifications.urls')),
    path('search/', include('apps.search.urls')),
    path('trash/', include('apps.trash.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Custom error handlers
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'
