"""
Admin configuration for Wallets app.
"""
from django.contrib import admin
from apps.wallets.models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'currency', 'is_active', 'created_at']
    list_filter = ['currency', 'is_active', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'balance', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'currency', 'is_active')
        }),
        ('Balance', {
            'fields': ('balance',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'wallet_user', 'transaction_type', 'amount', 'balance_after', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['wallet__user__email', 'reference', 'description']
    readonly_fields = ['id', 'wallet', 'transaction_type', 'amount', 'balance_after', 'created_at']
    date_hierarchy = 'created_at'
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def wallet_user(self, obj):
        return obj.wallet.user.email
    wallet_user.short_description = 'User'
