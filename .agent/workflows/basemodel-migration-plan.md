# BaseModel Migration Plan

## Overview

The new `BaseModel` includes all critical mixins built-in:
- **Timestamps**: `created_at`, `updated_at`
- **Soft Delete/Trash**: `is_active`, `trashed_at`, `trashed_by`, `permanent_delete_at`, `trash_reason`
- **Visibility**: `visibility`, `owner`, `allowed_users`, `allowed_groups`, `is_published`, `published_at`
- **Accountability (GDPR)**: `created_by`, `modified_by`, `consent_given`, `is_anonymized`, `retain_until`
- **Notifications**: `notifications_enabled`, `last_notified_at`, `watchers`
- **Search**: Class attributes `SEARCH_FIELDS`, `SEARCH_WEIGHTS`, etc.

## Key Issues to Resolve

1. **Field Conflicts**: Models that already have fields like `owner`, `created_by`, `watchers` will conflict
2. **Related Name Conflicts**: Multiple models with same related_name patterns
3. **Manager Conflicts**: Models with custom managers need to inherit from `BaseModelManager`
4. **System Models**: Some models (Notification, SearchIndex, TrashRegistry) should use `SimpleBaseModel`

---

## Phase 1: Core Infrastructure (Already Done)
- [x] Create enhanced `BaseModel` with all mixins
- [x] Create `SimpleBaseModel` for system/internal models
- [x] Create `BaseModelManager` with trash/visibility filtering
- [x] Update `core/models/__init__.py` exports

---

## Phase 2: System Apps (Use SimpleBaseModel)

These are internal/system apps that should NOT use the full BaseModel:

### 2.1 Notifications App
- [x] `Notification` → `SimpleBaseModel`
- [x] `NotificationPreference` → `SimpleBaseModel`

### 2.2 Search App  
- [x] `SearchIndex` → `SimpleBaseModel`
- [x] `SearchHistory` → `SimpleBaseModel`

### 2.3 Trash App
- [x] `TrashRegistry` → `SimpleBaseModel`

---

## Phase 3: Business Apps (Use Full BaseModel)

These apps contain business data and should use the full `BaseModel`:

### 3.1 Accounts App
**Models to review:**
- [x] `User` - Special case, extends AbstractUser (keep as-is, don't change to BaseModel)
- [x] `Profile` - Inherits BaseModel, checked for conflicts.

### 3.2 Policies App
**Models to review:**
- [x] `InsuranceProduct` - Resolved duplication by moving to CRM app.
- [x] `Policy` - Updated to use CRM product.
- [x] `PolicyApplication` - Updated to use CRM product.
- [x] `PolicyDocument` - Removed `uploaded_by`.

### 3.3 Claims App
**Models to review:**
- [x] `Claim` - Checked for conflicts.
- [x] `ClaimDocument` - Removed `uploaded_by`.
- [x] `ClaimNote` - Removed `author`.
- [x] `ClaimStatusHistory` - Migrated to `SimpleBaseModel`.

### 3.4 CRM App
**Models to review:**
- [x] `InsuranceProvider` - Checked.
- [x] `ProviderContact` - Checked.
- [x] `ProductCategory` - Checked.
- [x] `InsuranceProduct` - Consolidated with Policies product.
- [x] `ProductBenefit` - Checked.
- [x] `CustomerTag` - Checked.
- [x] `Customer` - Removed `created_by`.
- [x] `CustomerDocument` - Checked.
- [x] `Lead` - Removed `created_by`.
- [x] `Communication` - Checked.

### 3.5 Billing App
**Models to review:**
- [x] `Invoice` - Checked.
- [x] `Payment` - Removed `payment_date`.

### 3.6 Payments App
**Models to review:**
- [x] `PaymentNotification` - Migrated to `SimpleBaseModel`.

### 3.7 Wallets App
**Models to review:**
- [x] `Wallet` - Checked.
- [x] `WalletTransaction` - Checked.

### 3.8 Workflow App
**Models to review:**
- [x] `Department` - Checked.
- [x] `WorkClass` - Checked.
- [x] `AgentProfile` - Checked.
- [x] `Ticket` - Removed `created_by`.
- [x] `TicketActivity` - Migrated to `SimpleBaseModel`.
- [x] `AgentPerformance` - Migrated to `SimpleBaseModel`.

### 3.9 Integrations App
**Models to review:**
- [x] `IntegrationLog` - Migrated to `SimpleBaseModel`.
- [x] `WebhookEvent` - Migrated to `SimpleBaseModel`.

### 3.10 Core App (Landing Models)
**Models to review:**
- [x] Landing models migrated to `SimpleBaseModel`.

---

## Phase 4: Services Update

For each app, update services to use new BaseModel features:

### 4.1 Update service patterns:
```python
# Before
obj.save()

# After - with accountability
obj.created_by = request.user
obj.owner = request.user
obj.save()
```

### 4.2 Update trash handling:
```python
# Before
obj.is_active = False
obj.save()

# After
obj.trash(user=request.user, reason="User deleted")
```

### 4.3 Update visibility filtering:
```python
# Before
queryset = Model.objects.filter(some_field=value)

# After
queryset = Model.objects.visible_to(request.user).filter(some_field=value)
```

---

## Phase 5: Views Update

### 5.1 Update CreateViews:
- Set `created_by` and `owner` on form_valid

### 5.2 Update UpdateViews:
- Set `modified_by` on form_valid

### 5.3 Update DeleteViews:
- Use `obj.trash()` instead of `obj.delete()`

### 5.4 Update ListViews:
- Use `Model.objects.visible_to(user)` for queryset

---

## Phase 6: Admin Update

### 6.1 Update ModelAdmin classes:
- Add new fields to `list_display`
- Add `list_filter` for visibility, is_published, is_trashed
- Add `readonly_fields` for created_by, modified_by, trashed_at

---

## Phase 7: Migrations

### 7.1 Generate migrations:
```bash
python manage.py makemigrations
```

### 7.2 Review migrations for:
- Field additions (new BaseModel fields)
- Field removals (duplicate fields removed)
- Data migrations if needed

### 7.3 Apply migrations:
```bash
python manage.py migrate
```

---

## Phase 8: Testing

### 8.1 Run system check:
```bash
python manage.py check
```

### 8.2 Run existing tests:
```bash
python manage.py test
```

### 8.3 Test new features:
- Trash and restore functionality
- Visibility filtering
- Search across models
- Notification triggering

---

## Execution Order

1. **Phase 2**: System apps (already done)
2. **Phase 3.1**: Accounts app (User is special)
3. **Phase 3.2**: Policies app (core business)
4. **Phase 3.3**: Claims app
5. **Phase 3.4**: CRM app
6. **Phase 3.5-3.9**: Other business apps
7. **Phase 4-6**: Services, Views, Admin
8. **Phase 7**: Migrations
9. **Phase 8**: Testing

---

## Current Status

**Blockers**: 56 system check errors due to field/related_name conflicts

**Next Step**: Start with Phase 3.1 (Accounts App) to resolve conflicts methodically
