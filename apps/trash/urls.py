"""
Trash URL configuration.
"""
from django.urls import path
from . import views

app_name = 'trash'

urlpatterns = [
    # List and detail views
    path('', views.TrashListView.as_view(), name='list'),
    path('<int:pk>/', views.TrashDetailView.as_view(), name='detail'),
    
    # Single item actions
    path('<int:pk>/restore/', views.RestoreItemView.as_view(), name='restore'),
    path('<int:pk>/delete/', views.PermanentDeleteView.as_view(), name='delete'),
    
    # Bulk actions
    path('restore-multiple/', views.RestoreMultipleView.as_view(), name='restore_multiple'),
    path('delete-multiple/', views.DeleteMultipleView.as_view(), name='delete_multiple'),
    
    # Empty actions
    path('empty-expired/', views.EmptyExpiredView.as_view(), name='empty_expired'),
    path('empty-all/', views.EmptyAllView.as_view(), name='empty_all'),
    
    # API
    path('api/', views.TrashAPIView.as_view(), name='api'),
    
    # Widget
    path('widget/', views.TrashWidgetView.as_view(), name='widget'),
]
