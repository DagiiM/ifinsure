"""
Notification URL configuration.
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # List and detail views
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    
    # Actions
    path('<int:pk>/read/', views.MarkAsReadView.as_view(), name='mark_read'),
    path('read-all/', views.MarkAllAsReadView.as_view(), name='mark_all_read'),
    path('<int:pk>/archive/', views.ArchiveNotificationView.as_view(), name='archive'),
    path('<int:pk>/delete/', views.DeleteNotificationView.as_view(), name='delete'),
    
    # Preferences
    path('preferences/', views.NotificationPreferencesView.as_view(), name='preferences'),
    
    # API endpoints
    path('api/', views.NotificationAPIView.as_view(), name='api'),
    path('dropdown/', views.NotificationDropdownView.as_view(), name='dropdown'),
]
