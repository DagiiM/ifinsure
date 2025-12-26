from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # Dashboard
    path('', views.IntegrationsDashboardView.as_view(), name='dashboard'),
    
    # Categories
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category'),
    
    # Providers
    path('provider/<slug:slug>/', views.ProviderDetailView.as_view(), name='provider'),
    
    # Configuration
    path('configure/<slug:provider_slug>/', views.ConfigureProviderView.as_view(), name='configure'),
    path('config/<int:pk>/', views.ConfigDetailView.as_view(), name='config_detail'),
    path('config/<int:pk>/edit/', views.ConfigUpdateView.as_view(), name='config_edit'),
    path('config/<int:pk>/toggle/', views.ToggleConfigView.as_view(), name='toggle'),
    path('config/<int:pk>/test/', views.TestConnectionView.as_view(), name='test'),
    
    # Logs
    path('logs/', views.IntegrationLogsView.as_view(), name='logs'),
    path('logs/<int:pk>/', views.LogDetailView.as_view(), name='log_detail'),
    
    # Webhooks (external endpoint)
    path('webhooks/<slug:provider>/', views.WebhookView.as_view(), name='webhook'),
]
