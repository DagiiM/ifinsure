# ifinsure Production Readiness Implementation Plan

> **Version:** 1.0  
> **Created:** December 24, 2025  
> **Status:** Planning Phase  
> **Estimated Effort:** 4-6 weeks

---

## Executive Summary

This document outlines a comprehensive plan to transform ifinsure from a functional prototype into a production-ready insurance management system. The plan introduces an **Integrations Center** for managing payment providers, SMS gateways, and third-party services, while ensuring robust security, comprehensive testing, and enterprise-grade reliability.

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Architecture Overview](#2-architecture-overview)
3. [Phase 1: Foundation & Security](#phase-1-foundation--security-week-1)
4. [Phase 2: Integrations Center](#phase-2-integrations-center-week-2)
5. [Phase 3: Enhanced Features](#phase-3-enhanced-features-week-3)
6. [Phase 4: Testing & Quality](#phase-4-testing--quality-week-4)
7. [Phase 5: Production Deployment](#phase-5-production-deployment-week-5)
8. [Phase 6: Monitoring & Maintenance](#phase-6-monitoring--maintenance-week-6)
9. [Template Inventory](#template-inventory)
10. [API Documentation](#api-documentation)

---

## 1. Current State Assessment

### ✅ Completed Components

| Component | Status | Notes |
|-----------|--------|-------|
| Core App | ✅ Complete | BaseModel, AuditLog, mixins, utilities |
| Accounts App | ✅ Complete | Custom User model, Profile, authentication |
| Policies App | ✅ Complete | Products, applications, policies |
| Claims App | ✅ Complete | Claims workflow, documents, notes |
| Billing App | ✅ Complete | Invoices, payments |
| Dashboard App | ✅ Complete | Role-based dashboards |
| CSS Design System | ✅ Complete | Variables, components, responsive |
| Templates | ✅ Complete | All user-facing templates |
| Admin Configuration | ✅ Complete | All models registered |

### ❌ Missing Components

| Component | Priority | Phase |
|-----------|----------|-------|
| Integrations Center | Critical | Phase 2 |
| Unit/Integration Tests | Critical | Phase 4 |
| Email Notifications | High | Phase 3 |
| PDF Generation | High | Phase 3 |
| API Layer (REST) | Medium | Phase 3 |
| Production Deployment | High | Phase 5 |
| Monitoring & Logging | High | Phase 6 |

---

## 2. Architecture Overview

### Proposed System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Customer   │  │    Agent    │  │    Staff    │  │    Admin    │ │
│  │  Dashboard  │  │  Dashboard  │  │  Dashboard  │  │  Dashboard  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER (Django)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ Accounts │  │ Policies │  │  Claims  │  │ Billing  │  │  API   ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘│
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    INTEGRATIONS CENTER                        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │  │
│  │  │ Payment │  │   SMS   │  │  Email  │  │ Storage │          │  │
│  │  │Providers│  │ Gateway │  │ Service │  │ (S3/GCS)│          │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  PostgreSQL  │  │    Redis     │  │    Celery    │              │
│  │  (Primary)   │  │   (Cache)    │  │   (Tasks)    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation & Security (Week 1)

### 1.1 Environment Configuration

#### Tasks
- [ ] Create `.env.example` template
- [ ] Implement `python-decouple` for environment management
- [ ] Configure settings for dev/staging/production
- [ ] Set up secrets management

#### Files to Create/Modify
```
config/
├── settings/
│   ├── base.py (update for env vars)
│   ├── development.py (update)
│   └── production.py (update)
.env.example
.env (gitignored)
```

#### .env.example Template
```env
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ifinsure_db
DB_USER=ifinsure_user
DB_PASSWORD=secure-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-specific-password
DEFAULT_FROM_EMAIL=noreply@ifinsure.com

# Integrations
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=
MPESA_PASSKEY=
MPESA_ENVIRONMENT=sandbox

AFRICAS_TALKING_USERNAME=
AFRICAS_TALKING_API_KEY=

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=
```

### 1.2 Database Migration to PostgreSQL

#### Tasks
- [ ] Install PostgreSQL locally
- [ ] Create production database
- [ ] Update settings for PostgreSQL
- [ ] Test migrations
- [ ] Create backup scripts

### 1.3 Security Hardening

#### Tasks
- [ ] Implement rate limiting with django-ratelimit
- [ ] Add CSRF protection verification
- [ ] Configure Content Security Policy headers
- [ ] Set up secure cookie settings
- [ ] Implement password strength validation
- [ ] Add brute force protection for login
- [ ] File upload validation and sanitization

#### Files to Create
```
apps/core/
├── middleware/
│   ├── __init__.py
│   ├── security.py
│   └── rate_limit.py
├── validators.py
```

### 1.4 Logging Configuration

#### Tasks
- [ ] Set up structured JSON logging
- [ ] Configure log rotation
- [ ] Add request/response logging middleware
- [ ] Create audit trail for sensitive operations

#### Files to Create
```
apps/core/
├── logging.py
config/
├── logging_config.py
logs/
├── .gitkeep
```

---

## Phase 2: Integrations Center (Week 2)

### 2.1 Create Integrations App

This is a new Django app that provides a centralized hub for managing all third-party integrations.

#### App Structure
```
apps/integrations/
├── __init__.py
├── admin.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── payment.py
│   ├── sms.py
│   ├── email.py
│   └── storage.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── payments/
│   │   ├── __init__.py
│   │   ├── mpesa.py
│   │   ├── stripe.py
│   │   ├── paystack.py
│   │   └── flutterwave.py
│   ├── sms/
│   │   ├── __init__.py
│   │   ├── africastalking.py
│   │   └── twilio.py
│   ├── email/
│   │   ├── __init__.py
│   │   ├── smtp.py
│   │   └── sendgrid.py
│   └── storage/
│       ├── __init__.py
│       ├── s3.py
│       └── gcs.py
├── services.py
├── forms.py
├── views.py
├── urls.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   └── test_providers.py
└── migrations/
```

### 2.2 Integration Models

#### IntegrationCategory Model
```python
class IntegrationCategory(models.Model):
    """Categories for organizing integrations"""
    CATEGORIES = [
        ('payment', 'Payment Providers'),
        ('sms', 'SMS Gateways'),
        ('email', 'Email Services'),
        ('storage', 'File Storage'),
        ('analytics', 'Analytics'),
        ('crm', 'CRM Systems'),
    ]
    
    name = models.CharField(max_length=50, choices=CATEGORIES, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50)  # Icon class or emoji
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
```

#### IntegrationProvider Model
```python
class IntegrationProvider(BaseModel):
    """Available integration providers"""
    category = models.ForeignKey(IntegrationCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    logo = models.ImageField(upload_to='integrations/logos/', blank=True)
    website_url = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    provider_class = models.CharField(max_length=255)  # Python class path
    
    # Configuration schema (JSON)
    config_schema = models.JSONField(default=dict)
    
    # Feature flags
    supports_webhooks = models.BooleanField(default=False)
    supports_sandbox = models.BooleanField(default=True)
    
    # Availability
    is_available = models.BooleanField(default=True)
    countries = models.JSONField(default=list)  # ISO country codes
```

#### IntegrationConfig Model
```python
class IntegrationConfig(BaseModel):
    """Active integration configurations"""
    provider = models.ForeignKey(IntegrationProvider, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "Production M-Pesa"
    
    # Status
    is_enabled = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)  # Primary for category
    environment = models.CharField(max_length=20, choices=[
        ('sandbox', 'Sandbox/Test'),
        ('production', 'Production'),
    ])
    
    # Encrypted credentials
    credentials = models.JSONField(default=dict)  # Encrypted in DB
    
    # Webhook configuration
    webhook_url = models.URLField(blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    
    # Metadata
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(max_length=20, blank=True)
    
    class Meta:
        unique_together = ['provider', 'environment']
```

#### IntegrationLog Model
```python
class IntegrationLog(models.Model):
    """Log all integration activities"""
    config = models.ForeignKey(IntegrationConfig, on_delete=models.CASCADE)
    
    action = models.CharField(max_length=50)  # e.g., 'payment_initiated'
    request_data = models.JSONField(default=dict)
    response_data = models.JSONField(default=dict)
    
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ])
    error_message = models.TextField(blank=True)
    
    # Performance
    response_time_ms = models.PositiveIntegerField(null=True)
    
    # Reference
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2.3 Payment Provider Interface

#### Base Payment Provider
```python
# apps/integrations/providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from decimal import Decimal

@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    provider_reference: Optional[str] = None
    status: str = 'pending'
    message: str = ''
    raw_response: Dict[str, Any] = None

@dataclass
class PaymentRequest:
    amount: Decimal
    currency: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    description: str = ''
    reference: str = ''
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = None

class BasePaymentProvider(ABC):
    """Abstract base class for payment providers"""
    
    def __init__(self, config: 'IntegrationConfig'):
        self.config = config
        self.credentials = config.credentials
        
    @abstractmethod
    def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Initiate a payment request"""
        pass
    
    @abstractmethod
    def verify_payment(self, transaction_id: str) -> PaymentResult:
        """Verify payment status"""
        pass
    
    @abstractmethod
    def process_webhook(self, payload: Dict[str, Any]) -> PaymentResult:
        """Process incoming webhook"""
        pass
    
    @abstractmethod
    def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        """Initiate refund"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test provider connectivity"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def supported_currencies(self) -> list:
        pass
```

#### M-Pesa Provider Implementation
```python
# apps/integrations/providers/payments/mpesa.py

import requests
import base64
from datetime import datetime
from .base import BasePaymentProvider, PaymentRequest, PaymentResult

class MPesaProvider(BasePaymentProvider):
    """M-Pesa Daraja API Integration"""
    
    SANDBOX_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_URL = "https://api.safaricom.co.ke"
    
    provider_name = "M-Pesa"
    supported_currencies = ["KES"]
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = (
            self.PRODUCTION_URL 
            if config.environment == 'production' 
            else self.SANDBOX_URL
        )
        self._access_token = None
        self._token_expires = None
    
    def _get_access_token(self) -> str:
        """Get OAuth access token"""
        if self._access_token and self._token_expires > datetime.now():
            return self._access_token
            
        consumer_key = self.credentials.get('consumer_key')
        consumer_secret = self.credentials.get('consumer_secret')
        
        auth = base64.b64encode(
            f"{consumer_key}:{consumer_secret}".encode()
        ).decode()
        
        response = requests.get(
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {auth}"}
        )
        
        data = response.json()
        self._access_token = data['access_token']
        return self._access_token
    
    def initiate_payment(self, request: PaymentRequest) -> PaymentResult:
        """Initiate STK Push"""
        try:
            token = self._get_access_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            shortcode = self.credentials.get('shortcode')
            passkey = self.credentials.get('passkey')
            
            password = base64.b64encode(
                f"{shortcode}{passkey}{timestamp}".encode()
            ).decode()
            
            payload = {
                "BusinessShortCode": shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(request.amount),
                "PartyA": request.phone_number,
                "PartyB": shortcode,
                "PhoneNumber": request.phone_number,
                "CallBackURL": request.callback_url,
                "AccountReference": request.reference,
                "TransactionDesc": request.description
            }
            
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            data = response.json()
            
            if data.get('ResponseCode') == '0':
                return PaymentResult(
                    success=True,
                    transaction_id=data.get('CheckoutRequestID'),
                    provider_reference=data.get('MerchantRequestID'),
                    status='pending',
                    message='STK push sent successfully',
                    raw_response=data
                )
            else:
                return PaymentResult(
                    success=False,
                    status='failed',
                    message=data.get('errorMessage', 'Payment initiation failed'),
                    raw_response=data
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status='error',
                message=str(e)
            )
    
    def verify_payment(self, transaction_id: str) -> PaymentResult:
        """Query STK Push status"""
        # Implementation here
        pass
    
    def process_webhook(self, payload: dict) -> PaymentResult:
        """Process M-Pesa callback"""
        # Implementation here
        pass
    
    def refund_payment(self, transaction_id: str, amount=None) -> PaymentResult:
        """M-Pesa reversal"""
        # Implementation here
        pass
    
    def test_connection(self) -> bool:
        """Test API connectivity"""
        try:
            self._get_access_token()
            return True
        except:
            return False
```

### 2.4 Integrations Center Views

#### Admin Views
```python
# apps/integrations/views.py

from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.contrib.auth.mixins import UserPassesTestMixin
from .models import IntegrationCategory, IntegrationProvider, IntegrationConfig

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin

class IntegrationsDashboardView(AdminRequiredMixin, ListView):
    """Main integrations center dashboard"""
    model = IntegrationCategory
    template_name = 'integrations/dashboard.html'
    context_object_name = 'categories'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_integrations'] = IntegrationConfig.objects.filter(
            is_enabled=True
        ).count()
        context['total_providers'] = IntegrationProvider.objects.filter(
            is_available=True
        ).count()
        return context

class CategoryDetailView(AdminRequiredMixin, DetailView):
    """View providers in a category"""
    model = IntegrationCategory
    template_name = 'integrations/category_detail.html'
    context_object_name = 'category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['providers'] = IntegrationProvider.objects.filter(
            category=self.object,
            is_available=True
        )
        context['configs'] = IntegrationConfig.objects.filter(
            provider__category=self.object
        )
        return context

class ConfigureProviderView(AdminRequiredMixin, CreateView):
    """Configure a new integration"""
    model = IntegrationConfig
    template_name = 'integrations/configure.html'
    # Form defined dynamically based on provider schema

class TestConnectionView(AdminRequiredMixin, View):
    """Test integration connectivity"""
    def post(self, request, pk):
        config = get_object_or_404(IntegrationConfig, pk=pk)
        provider = get_provider_instance(config)
        
        success = provider.test_connection()
        config.last_tested_at = timezone.now()
        config.last_test_status = 'success' if success else 'failed'
        config.save()
        
        return JsonResponse({
            'success': success,
            'message': 'Connection successful' if success else 'Connection failed'
        })

class IntegrationLogsView(AdminRequiredMixin, ListView):
    """View integration activity logs"""
    model = IntegrationLog
    template_name = 'integrations/logs.html'
    paginate_by = 50
    ordering = ['-created_at']
```

### 2.5 Integrations Center Templates

#### Templates to Create
```
templates/integrations/
├── dashboard.html           # Main integrations center
├── category_detail.html     # Providers in category
├── provider_detail.html     # Provider information
├── configure.html           # Configure integration form
├── config_detail.html       # View/edit configuration
├── test_result.html         # Connection test results
├── logs.html                # Activity logs
├── webhooks.html            # Webhook configuration
└── partials/
    ├── provider_card.html
    ├── config_status.html
    └── log_entry.html
```

### 2.6 Integrations URL Configuration

```python
# apps/integrations/urls.py

from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('', views.IntegrationsDashboardView.as_view(), name='dashboard'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category'),
    path('provider/<slug:slug>/', views.ProviderDetailView.as_view(), name='provider'),
    path('configure/<slug:provider_slug>/', views.ConfigureProviderView.as_view(), name='configure'),
    path('config/<int:pk>/', views.ConfigDetailView.as_view(), name='config_detail'),
    path('config/<int:pk>/edit/', views.ConfigUpdateView.as_view(), name='config_edit'),
    path('config/<int:pk>/test/', views.TestConnectionView.as_view(), name='test'),
    path('config/<int:pk>/toggle/', views.ToggleConfigView.as_view(), name='toggle'),
    path('logs/', views.IntegrationLogsView.as_view(), name='logs'),
    path('webhooks/<slug:provider>/', views.WebhookView.as_view(), name='webhook'),
]
```

---

## Phase 3: Enhanced Features (Week 3)

### 3.1 Email Notification System

#### Tasks
- [ ] Create notifications app
- [ ] Implement email templates
- [ ] Set up async email sending with Celery
- [ ] Create notification preferences

#### Notification Types
| Event | Recipients | Template |
|-------|------------|----------|
| Policy Application Submitted | Customer, Agent | `application_submitted.html` |
| Policy Application Approved | Customer | `application_approved.html` |
| Policy Application Rejected | Customer | `application_rejected.html` |
| Policy Activated | Customer | `policy_activated.html` |
| Policy Expiring Soon | Customer | `policy_expiring.html` |
| Claim Submitted | Customer, Staff | `claim_submitted.html` |
| Claim Status Updated | Customer | `claim_status_update.html` |
| Claim Approved | Customer | `claim_approved.html` |
| Claim Paid | Customer | `claim_paid.html` |
| Invoice Created | Customer | `invoice_created.html` |
| Invoice Overdue | Customer | `invoice_overdue.html` |
| Payment Received | Customer | `payment_received.html` |
| Welcome Email | Customer | `welcome.html` |
| Password Reset | User | `password_reset.html` |

#### App Structure
```
apps/notifications/
├── __init__.py
├── models.py          # NotificationTemplate, NotificationLog
├── services.py        # EmailService, SMSService
├── tasks.py           # Celery async tasks
├── templates/
│   └── emails/
│       ├── base.html
│       ├── application_submitted.html
│       ├── policy_activated.html
│       └── ... (all templates)
└── signals.py         # Auto-trigger notifications
```

### 3.2 PDF Generation

#### Tasks
- [ ] Install WeasyPrint or ReportLab
- [ ] Create PDF templates
- [ ] Implement generation views
- [ ] Add download endpoints

#### PDF Documents
| Document | Template | Description |
|----------|----------|-------------|
| Policy Certificate | `policy_certificate.html` | Official policy document |
| Invoice | `invoice_pdf.html` | Printable invoice |
| Payment Receipt | `receipt_pdf.html` | Payment confirmation |
| Claim Summary | `claim_summary.html` | Claim details for customer |
| Statement | `statement.html` | Account statement |

### 3.3 REST API Layer

#### Tasks
- [ ] Install Django REST Framework
- [ ] Create API serializers
- [ ] Implement viewsets
- [ ] Add token authentication
- [ ] Generate API documentation

#### API Endpoints
```
/api/v1/
├── auth/
│   ├── login/
│   ├── logout/
│   ├── refresh/
│   └── me/
├── policies/
│   ├── products/
│   ├── applications/
│   └── policies/
├── claims/
├── billing/
│   ├── invoices/
│   └── payments/
└── webhooks/
    ├── mpesa/
    └── stripe/
```

### 3.4 Background Tasks (Celery)

#### Tasks
- [ ] Set up Redis as broker
- [ ] Configure Celery
- [ ] Implement periodic tasks
- [ ] Create async task handlers

#### Periodic Tasks
| Task | Schedule | Description |
|------|----------|-------------|
| `check_expiring_policies` | Daily | Send reminders for expiring policies |
| `check_overdue_invoices` | Daily | Update invoice statuses, send reminders |
| `cleanup_old_logs` | Weekly | Archive/delete old audit logs |
| `generate_reports` | Monthly | Generate monthly reports |
| `sync_integrations` | Hourly | Verify integration connectivity |

---

## Phase 4: Testing & Quality (Week 4)

### 4.1 Unit Tests

#### Test Coverage Requirements
- Models: 90%+
- Services: 95%+
- Views: 85%+
- Forms: 90%+
- Utils: 95%+

#### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── factories.py             # Model factories
├── core/
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_mixins.py
├── accounts/
│   ├── test_models.py
│   ├── test_views.py
│   └── test_forms.py
├── policies/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_views.py
├── claims/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_views.py
├── billing/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_views.py
└── integrations/
    ├── test_models.py
    └── test_providers.py
```

### 4.2 Integration Tests

#### Scenarios to Test
- [ ] Complete policy application flow
- [ ] Claims submission and processing
- [ ] Payment processing with mock providers
- [ ] Email delivery verification
- [ ] Webhook processing

### 4.3 Security Testing

#### Tasks
- [ ] Run OWASP ZAP scan
- [ ] Test authentication flows
- [ ] Verify CSRF protection
- [ ] Check SQL injection prevention
- [ ] Test file upload security
- [ ] Verify rate limiting

### 4.4 Performance Testing

#### Tasks
- [ ] Load test with Locust
- [ ] Database query optimization
- [ ] Cache implementation testing
- [ ] Response time benchmarking

---

## Phase 5: Production Deployment (Week 5)

### 5.1 Infrastructure Setup

#### Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env

  redis:
    image: redis:7-alpine

  celery:
    build: .
    command: celery -A config worker -l info
    env_file:
      - .env
    depends_on:
      - redis

  celery-beat:
    build: .
    command: celery -A config beat -l info
    env_file:
      - .env
    depends_on:
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./nginx.conf:/etc/nginx/nginx.conf

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### 5.2 CI/CD Pipeline

```yaml
# .github/workflows/main.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements/development.txt
      
      - name: Run tests
        run: |
          pytest --cov=apps --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    
    steps:
      - name: Deploy to production
        run: |
          # Deployment commands
```

### 5.3 Deployment Checklist

- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Enable HTTPS redirect
- [ ] Configure HSTS
- [ ] Set secure cookies
- [ ] Configure CORS if needed
- [ ] Set up database backups
- [ ] Configure logging
- [ ] Set up monitoring alerts
- [ ] Test email delivery
- [ ] Verify static files serving
- [ ] Test media file uploads
- [ ] Verify all integrations

---

## Phase 6: Monitoring & Maintenance (Week 6)

### 6.1 Application Monitoring

#### Sentry Integration
```python
# config/settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
)
```

### 6.2 Health Checks

#### Endpoints
```
/health/           # Basic health check
/health/db/        # Database connectivity
/health/redis/     # Redis connectivity
/health/celery/    # Celery worker status
/health/integrations/  # Integration status
```

### 6.3 Metrics Dashboard

#### Key Metrics to Track
- Request rate and latency
- Error rate
- Database connection pool
- Cache hit rate
- Background task queue length
- Payment success rate
- Active users

### 6.4 Backup & Recovery

#### Backup Schedule
| Type | Frequency | Retention |
|------|-----------|-----------|
| Database full | Daily | 30 days |
| Database incremental | Hourly | 7 days |
| Media files | Daily | 90 days |
| Configuration | On change | Indefinite |

---

## Template Inventory

### Complete Template Checklist

#### Base Templates
- [x] `base.html` - Main layout
- [x] `includes/sidebar.html`
- [x] `includes/header.html`
- [x] `includes/messages.html`
- [x] `includes/pagination.html`

#### Error Pages
- [x] `errors/404.html`
- [x] `errors/500.html`
- [x] `errors/403.html` ✅ Complete
- [x] `errors/400.html` ✅ Complete

#### Accounts
- [x] `accounts/login.html`
- [x] `accounts/register.html`
- [x] `accounts/profile.html`
- [x] `accounts/profile_edit.html`
- [x] `accounts/password_change.html`
- [x] `accounts/password_reset.html` ✅ Complete
- [x] `accounts/password_reset_confirm.html` ✅ Complete
- [x] `accounts/password_reset_done.html` ✅ Complete

#### Dashboard
- [x] `dashboard/customer.html`
- [x] `dashboard/agent.html`
- [x] `dashboard/staff.html`
- [x] `dashboard/admin.html`

#### Policies (Customer)
- [x] `policies/list.html`
- [x] `policies/detail.html`
- [x] `policies/products.html`
- [x] `policies/product_detail.html`
- [x] `policies/apply.html`
- [x] `policies/applications.html`
- [x] `policies/application_detail.html`

#### Policies (Agent)
- [x] `policies/agent/policy_list.html`
- [x] `policies/agent/application_list.html`
- [x] `policies/agent/application_review.html`

#### Claims (Customer)
- [x] `claims/list.html`
- [x] `claims/detail.html`
- [x] `claims/create.html`
- [x] `claims/edit.html` ✅ Complete

#### Claims (Staff)
- [x] `claims/staff/claim_list.html`
- [x] `claims/staff/claim_detail.html`

#### Billing (Customer)
- [x] `billing/invoices.html`
- [x] `billing/invoice_detail.html`
- [x] `billing/payment.html`
- [x] `billing/payment_success.html` ✅ Complete
- [x] `billing/payment_failed.html` ✅ Complete

#### Billing (Staff)
- [x] `billing/staff/invoice_list.html`
- [x] `billing/staff/invoice_detail.html`
- [x] `billing/staff/invoice_create.html`

#### Integrations Center (Admin)
- [x] `integrations/dashboard.html` ✅ Complete
- [x] `integrations/category_detail.html` ✅ Complete
- [ ] `integrations/provider_detail.html` - **TO CREATE**
- [x] `integrations/configure.html` ✅ Complete
- [x] `integrations/config_detail.html` ✅ Complete
- [x] `integrations/logs.html` ✅ Complete
- [ ] `integrations/webhooks.html` - **TO CREATE**

#### Reports (Admin) - **ALL TO CREATE**
- [ ] `reports/dashboard.html`
- [ ] `reports/policies.html`
- [ ] `reports/claims.html`
- [ ] `reports/revenue.html`

#### Settings (Admin) - **ALL TO CREATE**
- [ ] `settings/general.html`
- [ ] `settings/branding.html`
- [ ] `settings/email.html`
- [ ] `settings/security.html`

#### Email Templates ✅ Complete
- [x] `emails/base.html`
- [x] `emails/welcome.html`
- [x] `emails/application_submitted.html`
- [x] `emails/application_approved.html`
- [x] `emails/application_rejected.html`
- [x] `emails/policy_activated.html`
- [x] `emails/policy_expiring.html`
- [x] `emails/claim_submitted.html`
- [x] `emails/claim_status_update.html`
- [x] `emails/invoice_created.html`
- [x] `emails/invoice_overdue.html`
- [x] `emails/payment_received.html`
- [x] `emails/password_reset.html`

#### PDF Templates ✅ Complete
- [x] `pdf/base.html`
- [x] `pdf/policy_certificate.html`
- [x] `pdf/invoice.html`
- [x] `pdf/receipt.html`
- [x] `pdf/claim_summary.html`
- [x] `pdf/statement.html`


---

## API Documentation

### Authentication
All API endpoints (except auth) require Bearer token authentication.

```
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
POST /api/v1/auth/refresh/
GET  /api/v1/auth/me/
```

### Policies API
```
GET    /api/v1/policies/products/
GET    /api/v1/policies/products/{id}/
GET    /api/v1/policies/applications/
POST   /api/v1/policies/applications/
GET    /api/v1/policies/applications/{id}/
GET    /api/v1/policies/policies/
GET    /api/v1/policies/policies/{id}/
```

### Claims API
```
GET    /api/v1/claims/
POST   /api/v1/claims/
GET    /api/v1/claims/{id}/
PATCH  /api/v1/claims/{id}/
POST   /api/v1/claims/{id}/documents/
```

### Billing API
```
GET    /api/v1/billing/invoices/
GET    /api/v1/billing/invoices/{id}/
POST   /api/v1/billing/invoices/{id}/pay/
GET    /api/v1/billing/payments/
```

### Webhook Endpoints
```
POST /api/v1/webhooks/mpesa/
POST /api/v1/webhooks/stripe/
POST /api/v1/webhooks/paystack/
```

---

## Dependencies Update

### requirements/base.txt
```
Django>=5.1,<6.0
python-decouple>=3.8
Pillow>=10.0
python-dateutil>=2.8
```

### requirements/production.txt
```
-r base.txt

# Database
psycopg2-binary>=2.9

# Server
gunicorn>=22.0
whitenoise>=6.7

# Cache & Queue
redis>=5.0
celery>=5.3

# API
djangorestframework>=3.14
djangorestframework-simplejwt>=5.3

# Security
django-cors-headers>=4.3

# PDF Generation
weasyprint>=60.0

# Monitoring
sentry-sdk>=1.39

# Storage
boto3>=1.34  # For S3
django-storages>=1.14
```

### requirements/development.txt
```
-r base.txt

# Debug
django-debug-toolbar>=4.4

# Testing
pytest>=8.0
pytest-django>=4.7
pytest-cov>=4.1
factory-boy>=3.3

# Code Quality
black>=24.0
isort>=5.13
flake8>=7.0
mypy>=1.8
```

---

## Summary

### Timeline Overview

| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 1 | Week 1 | Foundation, Security, Environment |
| Phase 2 | Week 2 | Integrations Center |
| Phase 3 | Week 3 | Email, PDF, API, Background Tasks |
| Phase 4 | Week 4 | Testing & Quality Assurance |
| Phase 5 | Week 5 | Production Deployment |
| Phase 6 | Week 6 | Monitoring & Maintenance |

### Deliverables Checklist

- [ ] Environment configuration with `.env`
- [ ] PostgreSQL database migration
- [ ] Security hardening complete
- [ ] Integrations Center app
- [ ] Payment provider integrations (M-Pesa, etc.)
- [ ] Email notification system
- [ ] PDF generation
- [ ] REST API layer
- [ ] Celery background tasks
- [ ] 85%+ test coverage
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Monitoring & alerting
- [ ] Documentation complete

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Integration API changes | Use adapter pattern, version APIs |
| Security vulnerabilities | Regular dependency updates, security scans |
| Performance issues | Load testing, caching, database optimization |
| Data loss | Automated backups, disaster recovery plan |
| Provider downtime | Multiple provider fallbacks |

---

*This document should be reviewed and updated as implementation progresses.*
