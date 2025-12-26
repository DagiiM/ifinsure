"""
Billing URL configuration.
"""
from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Customer views
    path('', views.InvoiceListView.as_view(), name='invoices'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('<int:invoice_pk>/pay/', views.CustomerPaymentView.as_view(), name='pay'),
    
    # Staff views
    path('staff/', views.StaffInvoiceListView.as_view(), name='staff_invoices'),
    path('staff/create/', views.StaffInvoiceCreateView.as_view(), name='staff_invoice_create'),
    path('staff/<int:pk>/', views.StaffInvoiceDetailView.as_view(), name='staff_invoice_detail'),
]
