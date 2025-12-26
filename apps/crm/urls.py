"""
URL configuration for CRM app.
"""
from django.urls import path
from apps.crm import views

app_name = 'crm'

urlpatterns = [
    # Dashboard
    path('', views.CRMDashboardView.as_view(), name='dashboard'),
    
    # Providers
    path('providers/', views.ProviderListView.as_view(), name='provider_list'),
    path('providers/<uuid:pk>/', views.ProviderDetailView.as_view(), name='provider_detail'),
    
    # Products
    path('products/', views.ProductCatalogView.as_view(), name='product_catalog'),
    path('products/<str:code>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/new/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<uuid:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    
    # Leads
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
    path('leads/<uuid:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
]
