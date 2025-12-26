"""
Claims URL configuration.
"""
from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    # Customer views
    path('', views.ClaimListView.as_view(), name='list'),
    path('create/', views.ClaimCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ClaimDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ClaimUpdateView.as_view(), name='edit'),
    
    # Staff views
    path('staff/', views.StaffClaimListView.as_view(), name='staff_list'),
    path('staff/<int:pk>/', views.StaffClaimDetailView.as_view(), name='staff_detail'),
]
