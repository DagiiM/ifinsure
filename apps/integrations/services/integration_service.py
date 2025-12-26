from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Avg
from apps.core.services.base import BaseService, service_action
from apps.integrations.models import (
    IntegrationCategory, IntegrationProvider, 
    IntegrationConfig, IntegrationLog, WebhookEvent
)


class IntegrationService(BaseService):
    """Business logic for integration operations."""
    
    model = IntegrationConfig
    
    # ============ CONFIGURATION OPERATIONS ============
    
    @service_action(audit=True)
    def create_config(
        self,
        provider: IntegrationProvider,
        name: str,
        credentials: dict,
        environment: str = 'sandbox',
        is_enabled: bool = False,
        settings: dict = None
    ) -> IntegrationConfig:
        """
        Create a new integration configuration.
        """
        if not provider:
            raise ValueError('Provider is required')
        
        if not name:
            raise ValueError('Configuration name is required')
        
        # Check for duplicate environment configs
        if IntegrationConfig.objects.filter(
            provider=provider,
            environment=environment
        ).exists():
            raise ValueError(
                f'A {environment} configuration already exists for {provider.name}'
            )
        
        config = self.create(
            provider=provider,
            name=name,
            credentials=credentials,
            environment=environment,
            is_enabled=is_enabled,
            settings=settings or {}
        )
        
        return config
    
    @service_action(audit=True)
    def update_config(
        self,
        config: IntegrationConfig,
        **fields
    ) -> IntegrationConfig:
        """
        Update an integration configuration.
        """
        allowed_fields = ['name', 'credentials', 'settings', 'is_enabled']
        update_data = {k: v for k, v in fields.items() if k in allowed_fields}
        
        return self.update(config, **update_data)
    
    @service_action(audit=True)
    def toggle_config(self, config: IntegrationConfig) -> IntegrationConfig:
        """
        Toggle an integration config enabled/disabled.
        """
        return self.update_config(config, is_enabled=not config.is_enabled)
    
    @service_action(audit=True)
    def delete_config(self, config: IntegrationConfig) -> bool:
        """
        Delete an integration configuration.
        """
        return self.delete(config, soft=False)  # We want hard delete for configs
    
    # ============ CONNECTION TESTING ============
    
    def test_connection(self, config: IntegrationConfig) -> dict:
        """
        Test the connection to an integration provider.
        """
        success = config.test_connection()
        
        return {
            'success': success,
            'message': config.last_test_message,
            'status': config.last_test_status,
            'tested_at': config.last_tested_at
        }
    
    # ============ WEBHOOK PROCESSING ============
    
    @service_action(audit=True)
    def process_webhook(
        self,
        provider_slug: str,
        payload: dict,
        headers: dict,
        ip_address: str = ''
    ) -> dict:
        """
        Process an incoming webhook.
        """
        try:
            provider = IntegrationProvider.objects.get(slug=provider_slug)
        except IntegrationProvider.DoesNotExist:
            raise ValueError(f'Unknown provider: {provider_slug}')
        
        config = IntegrationConfig.objects.filter(
            provider=provider,
            is_enabled=True
        ).first()
        
        if not config:
            raise ValueError('No active configuration for this provider')
        
        # Store webhook event
        event = WebhookEvent.objects.create(
            config=config,
            event_type=payload.get('event', payload.get('type', 'unknown')),
            payload=payload,
            headers=headers,
            ip_address=ip_address
        )
        
        # Process webhook
        try:
            provider_instance = config.get_provider_instance()
            result = provider_instance.process_webhook(payload)
            event.mark_processed()
            
            # Log success
            IntegrationLog.log_request(
                config=config,
                action='webhook_received',
                request_data=payload,
                response_data={'processed': True},
                status='success',
                ip_address=ip_address
            )
            
            return {'success': True, 'message': 'Webhook processed'}
            
        except Exception as e:
            event.mark_failed(str(e))
            
            IntegrationLog.log_request(
                config=config,
                action='webhook_failed',
                request_data=payload,
                status='failed',
                error_message=str(e),
                ip_address=ip_address
            )
            
            return {'success': False, 'message': str(e)}
    
    # ============ STATISTICS ============
    
    def get_dashboard_statistics(self) -> dict:
        """Get statistics for the integrations dashboard."""
        today = timezone.now().replace(hour=0, minute=0, second=0)
        week_ago = today - timedelta(days=7)
        
        return {
            'active_integrations': IntegrationConfig.objects.filter(
                is_enabled=True
            ).count(),
            'total_providers': IntegrationProvider.objects.filter(
                is_available=True
            ).count(),
            'needs_attention': IntegrationConfig.objects.filter(
                is_enabled=True,
                last_test_status='failed'
            ).count(),
            'api_calls_today': IntegrationLog.objects.filter(
                created_at__gte=today
            ).count(),
            'api_calls_week': IntegrationLog.objects.filter(
                created_at__gte=week_ago
            ).count(),
            'success_rate': self._calculate_success_rate(week_ago),
        }
    
    def _calculate_success_rate(self, since) -> float:
        """Calculate success rate for logs since a given date."""
        logs = IntegrationLog.objects.filter(created_at__gte=since)
        total = logs.count()
        
        if total == 0:
            return 100.0
        
        success = logs.filter(status='success').count()
        return round((success / total) * 100, 1)
    
    def get_config_statistics(self, config: IntegrationConfig) -> dict:
        """Get usage statistics for a specific config."""
        today = timezone.now().replace(hour=0, minute=0, second=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        logs = IntegrationLog.objects.filter(config=config)
        
        return {
            'today': logs.filter(created_at__gte=today).count(),
            'week': logs.filter(created_at__gte=week_ago).count(),
            'month': logs.filter(created_at__gte=month_ago).count(),
            'success_rate': self._calculate_config_success_rate(config),
            'avg_response_time': logs.aggregate(
                avg=Avg('response_time_ms')
            )['avg'] or 0,
        }
    
    def _calculate_config_success_rate(self, config: IntegrationConfig) -> float:
        """Calculate success rate for a specific config."""
        week_ago = timezone.now() - timedelta(days=7)
        logs = IntegrationLog.objects.filter(
            config=config,
            created_at__gte=week_ago
        )
        total = logs.count()
        
        if total == 0:
            return 100.0
        
        success = logs.filter(status='success').count()
        return round((success / total) * 100, 1)
    
    # ============ QUERIES ============
    
    def get_categories(self, active_only: bool = True):
        """Get integration categories."""
        qs = IntegrationCategory.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by('display_order')
    
    def get_providers(self, category=None, available_only: bool = True):
        """Get integration providers."""
        qs = IntegrationProvider.objects.all()
        if available_only:
            qs = qs.filter(is_available=True)
        if category:
            qs = qs.filter(category=category)
        return qs.select_related('category')
    
    def get_configs(self, provider=None, enabled_only: bool = False):
        """Get integration configurations."""
        qs = IntegrationConfig.objects.all()
        if provider:
            qs = qs.filter(provider=provider)
        if enabled_only:
            qs = qs.filter(is_enabled=True)
        return qs.select_related('provider', 'provider__category')
    
    def get_logs(
        self,
        config=None,
        status: str = None,
        date_range: str = 'week',
        limit: int = None
    ):
        """Get integration logs with filters."""
        qs = IntegrationLog.objects.select_related(
            'config', 'config__provider'
        ).order_by('-created_at')
        
        if config:
            qs = qs.filter(config=config)
        
        if status:
            qs = qs.filter(status=status)
        
        today = timezone.now().replace(hour=0, minute=0, second=0)
        
        if date_range == 'today':
            qs = qs.filter(created_at__gte=today)
        elif date_range == 'week':
            qs = qs.filter(created_at__gte=today - timedelta(days=7))
        elif date_range == 'month':
            qs = qs.filter(created_at__gte=today - timedelta(days=30))
        
        if limit:
            qs = qs[:limit]
        
        return qs
    
    def get_recent_logs(self, limit: int = 10):
        """Get most recent integration logs."""
        return self.get_logs(limit=limit)
