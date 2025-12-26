# Base Class Refactoring Plan

Objective: Refactor all views and services to inherit from `BaseView` and `BaseService` classes in `apps/core`.

## Services Refactor

- [x] `accounts/services/account_service.py`
- [x] `billing/services/billing_service.py`
- [x] `claims/services/claim_service.py`
- [x] `crm/services/crm_service.py`
- [x] `integrations/services/integration_service.py`
- [x] `payments/services/payment_service.py`
- [x] `policies/services/application_payment_service.py`
- [x] `policies/services/policy_service.py`
- [x] `wallets/services/wallet_service.py`
- [x] `workflow/services/assignment_service.py`
- [x] `workflow/services/performance_service.py`
- [x] `workflow/services/ticket_service.py`

## Views Refactor

- [ ] `accounts/views.py`
- [ ] `billing/views.py`
- [ ] `claims/views.py`
- [ ] `core/views/core_views.py`
- [ ] `crm/views.py`
- [ ] `dashboard/views.py`
- [ ] `integrations/views.py`
- [ ] `payments/views.py`
- [ ] `policies/views.py`
- [ ] `wallets/views.py`
- [ ] `workflow/views.py`

## Guidelines

1. Inherit from `BaseService` or `BaseView` (and its specialized versions like `BaseListView`, `BaseAPIView`).
2. Update imports.
3. Use `BaseService` methods where applicable (CRUD, pagination).
4. Use `@service_action` decorator for service methods to handle transactions and auditing automatically.
5. Use `BaseView` helpers for context, messages, and JSON responses.
