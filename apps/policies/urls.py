"""
Policies URL configuration.
"""
from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    # ================================
    # PUBLIC ROUTES (No Login Required)
    # ================================
    
    # Products marketplace (public)
    path('products/', views.PublicProductListView.as_view(), name='products'),
    path('products/<uuid:pk>/', views.PublicProductDetailView.as_view(), name='product_detail'),
    
    # Cart (session-based, works for anonymous)
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<uuid:pk>/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/update/<uuid:pk>/', views.CartUpdateView.as_view(), name='cart_update'),
    path('cart/remove/<uuid:pk>/', views.CartRemoveView.as_view(), name='cart_remove'),
    path('cart/clear/', views.CartClearView.as_view(), name='cart_clear'),
    path('cart/checkout/', views.CartCheckoutView.as_view(), name='checkout'),
    
    # ================================
    # CUSTOMER ROUTES (Login Required)
    # ================================
    
    # My Policies
    path('', views.PolicyListView.as_view(), name='list'),
    path('<int:pk>/', views.PolicyDetailView.as_view(), name='detail'),
    
    # Applications
    path('apply/', views.ApplicationCreateView.as_view(), name='apply'),
    path('apply/from-cart/', views.ApplyFromCartView.as_view(), name='apply_from_cart'),
    path('applications/', views.ApplicationListView.as_view(), name='applications'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    
    # ================================
    # AGENT/STAFF ROUTES
    # ================================
    path('agent/', views.AgentPolicyListView.as_view(), name='agent_policies'),
    path('agent/applications/', views.AgentApplicationListView.as_view(), name='agent_applications'),
    path('agent/applications/<int:pk>/review/', views.AgentApplicationReviewView.as_view(), name='application_review'),
]
