"""
Dashboard URL configuration.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardHomeView.as_view(), name='home'),
    path('customer/', views.CustomerDashboardView.as_view(), name='customer'),
    path('agent/', views.AgentDashboardView.as_view(), name='agent'),
    path('staff/', views.StaffDashboardView.as_view(), name='staff'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
]
