"""
URL configuration for wallets app.
"""
from django.urls import path
from apps.wallets import views

app_name = 'wallets'

urlpatterns = [
    path('', views.WalletDashboardView.as_view(), name='wallet'),
    path('transactions/', views.WalletTransactionsView.as_view(), name='transactions'),
    path('deposit/', views.WalletDepositView.as_view(), name='deposit'),
    
    # M-Pesa STK Push flow
    path('deposit/<str:payment_ref>/mpesa/', views.MpesaSTKView.as_view(), name='mpesa_stk'),
    path('deposit/<str:payment_ref>/mpesa/status/', views.MpesaStatusView.as_view(), name='mpesa_status'),
    
    # Bank P2P flow
    path('deposit/<str:payment_ref>/proof/', views.DepositProofView.as_view(), name='deposit_proof'),
    
    # Generic process (fallback)
    path('deposit/<str:payment_ref>/process/', views.DepositProcessView.as_view(), name='deposit_process'),
]
