# CRM & Enhanced Integrations System
## Comprehensive Implementation Proposal

**Project:** ifinsure Insurance Management System  
**Module:** CRM & Partner Integrations  
**Date:** December 25, 2024  

---

## 1. Executive Summary

This proposal outlines the implementation of a robust Customer Relationship Management (CRM) system designed for insurance brokerage operations. The system will manage:

- **Insurance Providers** (Underwriters like Britam, Jubilee, etc.)
- **Insurance Products** (linked to providers with commission tracking)
- **Customers** (Individuals and Corporate clients)
- **Leads & Prospects** (with conversion tracking)
- **Communication History** (calls, emails, SMS, notes)
- **Enhanced Integrations** (M-Pesa, SMS, Email, Provider APIs)

---

## 2. Data Model Design

### 2.1 Provider Management

```
┌─────────────────────────────────────────────────────────────────┐
│                     InsuranceProvider                            │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ name (str) - e.g., "Britam Insurance"                           │
│ code (str, unique) - e.g., "BRITAM"                             │
│ provider_type (enum) - underwriter, reinsurer, broker           │
│ logo (image)                                                     │
│                                                                  │
│ # Contact Information                                            │
│ email, phone, website                                           │
│ address                                                          │
│                                                                  │
│ # Business Details                                               │
│ registration_number                                              │
│ ira_license (Insurance Regulatory Authority)                    │
│ default_commission_rate (decimal)                                │
│                                                                  │
│ # API Integration                                                │
│ api_enabled (bool)                                              │
│ api_base_url                                                     │
│ api_credentials (encrypted JSON)                                 │
│                                                                  │
│ # Contract                                                       │
│ contract_start, contract_end                                     │
│ contract_document (file)                                         │
│                                                                  │
│ is_active, created_at, updated_at                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ProviderContact                              │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ provider (FK)                                                    │
│ name, title, department                                          │
│ email, phone                                                     │
│ is_primary (bool)                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Catalog

```
┌─────────────────────────────────────────────────────────────────┐
│                     ProductCategory                              │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ name - e.g., "Motor", "Health", "Life", "Property"              │
│ code                                                             │
│ description                                                      │
│ icon                                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     InsuranceProduct                             │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ provider (FK InsuranceProvider)                                  │
│ category (FK ProductCategory)                                    │
│                                                                  │
│ name - e.g., "Britam Motor Comprehensive"                       │
│ code (unique)                                                    │
│ description                                                      │
│                                                                  │
│ # Pricing                                                        │
│ base_premium (decimal)                                          │
│ premium_type (enum) - fixed, percentage, calculated             │
│ min_premium                                                      │
│ pricing_rules (JSON) - age factors, risk factors, etc.          │
│                                                                  │
│ # Coverage                                                       │
│ coverage_details (JSON)                                         │
│ exclusions (text)                                                │
│ terms_conditions (text)                                          │
│ policy_document_template (file)                                  │
│                                                                  │
│ # Commission                                                     │
│ commission_rate (decimal)                                        │
│ commission_type (enum) - percentage, fixed                       │
│                                                                  │
│ # Settings                                                       │
│ is_active                                                        │
│ requires_underwriting (bool)                                    │
│ auto_renew_enabled (bool)                                       │
│                                                                  │
│ created_at, updated_at                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ProductBenefit                               │
├─────────────────────────────────────────────────────────────────┤
│ product (FK)                                                     │
│ name - e.g., "Third Party Liability"                            │
│ description                                                      │
│ coverage_amount                                                  │
│ is_included (bool)                                              │
│ is_optional (bool)                                              │
│ additional_premium                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Customer Management

```
┌─────────────────────────────────────────────────────────────────┐
│                       Customer                                   │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ customer_type (enum) - individual, corporate                     │
│ customer_number (auto-generated)                                 │
│                                                                  │
│ # User Link                                                      │
│ user (FK, nullable) - linked user account                       │
│                                                                  │
│ # Individual Fields                                              │
│ first_name, last_name                                           │
│ id_type (enum) - national_id, passport, alien_id                │
│ id_number                                                        │
│ date_of_birth                                                    │
│ gender                                                           │
│ occupation                                                       │
│                                                                  │
│ # Corporate Fields                                               │
│ company_name                                                     │
│ company_registration                                             │
│ kra_pin                                                          │
│ industry                                                         │
│                                                                  │
│ # Contact                                                        │
│ email, phone, alt_phone                                         │
│ address, city, county, postal_code                              │
│                                                                  │
│ # CRM Fields                                                     │
│ source (enum) - walk_in, referral, online, agent, etc.          │
│ assigned_agent (FK User)                                        │
│ lead_score (int)                                                │
│ lifecycle_stage (enum) - lead, prospect, customer, churned      │
│ tags (M2M)                                                       │
│                                                                  │
│ # Preferences                                                    │
│ preferred_contact_method                                         │
│ marketing_consent                                                │
│ sms_consent                                                      │
│                                                                  │
│ # Metadata                                                       │
│ notes                                                            │
│ created_at, updated_at                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    CustomerDocument                              │
├─────────────────────────────────────────────────────────────────┤
│ customer (FK)                                                    │
│ document_type (enum) - id, kra, passport, photo, etc.           │
│ file                                                             │
│ verified (bool)                                                 │
│ uploaded_at                                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Leads & Communication

```
┌─────────────────────────────────────────────────────────────────┐
│                         Lead                                     │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ customer (FK, nullable) - converts to customer                   │
│                                                                  │
│ # Contact Info                                                   │
│ name, email, phone                                              │
│                                                                  │
│ # Lead Details                                                   │
│ source (enum) - website, referral, social, walk_in, etc.        │
│ interest (FK ProductCategory or Product)                         │
│ notes                                                            │
│                                                                  │
│ # Pipeline                                                       │
│ status (enum) - new, contacted, qualified, proposal, won, lost  │
│ assigned_to (FK User)                                           │
│                                                                  │
│ # Tracking                                                       │
│ follow_up_date                                                   │
│ last_contact_at                                                  │
│ converted_at                                                     │
│ lost_reason                                                      │
│                                                                  │
│ created_at, updated_at                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Communication                                 │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ customer (FK, nullable)                                          │
│ lead (FK, nullable)                                             │
│                                                                  │
│ channel (enum) - call, sms, email, whatsapp, meeting, note      │
│ direction (enum) - inbound, outbound                            │
│ subject                                                          │
│ content                                                          │
│                                                                  │
│ performed_by (FK User)                                          │
│ outcome (str) - e.g., "Scheduled callback", "Sent quote"        │
│                                                                  │
│ created_at                                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Enhanced Integrations

```
┌─────────────────────────────────────────────────────────────────┐
│                    IntegrationProvider                           │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ name - e.g., "Safaricom M-Pesa", "Africa's Talking"             │
│ code (unique) - e.g., "mpesa", "at_sms"                         │
│ category (enum) - payment, sms, email, insurance_api, other     │
│                                                                  │
│ is_active                                                        │
│ is_configured                                                    │
│                                                                  │
│ # Configuration                                                  │
│ config (encrypted JSON) - API keys, secrets, URLs               │
│ test_mode (bool)                                                │
│ test_config (encrypted JSON)                                    │
│                                                                  │
│ # Health                                                         │
│ last_health_check                                                │
│ health_status (enum) - healthy, degraded, down                  │
│                                                                  │
│ created_at, updated_at                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    IntegrationLog                                │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ provider (FK)                                                    │
│ action - e.g., "stk_push", "send_sms"                           │
│ request_data (JSON)                                             │
│ response_data (JSON)                                            │
│ status (enum) - success, failed, pending                        │
│ error_message                                                    │
│ duration_ms                                                      │
│ created_at                                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Webhook                                     │
├─────────────────────────────────────────────────────────────────┤
│ id (UUID)                                                        │
│ provider (FK)                                                    │
│ event_type                                                       │
│ payload (JSON)                                                   │
│ processed (bool)                                                │
│ processed_at                                                     │
│ created_at                                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Plan

### Phase 1: CRM Core ✅ COMPLETE
- [x] Create `crm` app
- [x] InsuranceProvider model
- [x] ProductCategory model  
- [x] InsuranceProduct model
- [x] ProductBenefit model
- [x] Customer model
- [x] CustomerDocument model
- [x] Lead model
- [x] Communication model
- [x] Admin interfaces

### Phase 2: CRM Views & Templates ✅ COMPLETE
- [x] CRM Dashboard
- [x] Provider list and detail views
- [x] Product catalog with filtering
- [x] Product detail with benefits
- [x] Customer list with search
- [x] Lead pipeline view

### Phase 3: Initial Data ✅ COMPLETE
- [x] Management command `setup_crm`
- [x] 6 Insurance providers
- [x] 9 Product categories
- [x] 7 Sample products with benefits

### Phase 4: Integration with Existing Apps (TODO)
- [ ] Update Policy to link to InsuranceProduct
- [ ] Update Policy to link to Customer
- [ ] Migration scripts
- [ ] Customer 360° view with policies

---

## 4. Default Data

### Insurance Providers
- Britam Insurance
- Jubilee Insurance  
- UAP Old Mutual
- APA Insurance
- CIC Insurance
- Madison Insurance

### Product Categories
- Motor (Comprehensive, Third Party)
- Health (Individual, Group)
- Life (Term, Whole Life, Endowment)
- Property (Fire, Burglary, All Risks)
- Travel
- Personal Accident

---

*Prepared for ifinsure by Antigravity AI*
