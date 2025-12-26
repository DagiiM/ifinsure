# Core Framework - Base Classes and Mixins

## Summary

The core app now provides a comprehensive framework of base classes and mixins that ensure consistency, compliance, and maintainability across the entire application.

---

## Core App Structure

```
apps/core/
├── admin/
│   ├── __init__.py
│   ├── admin.py          # Model-specific admins
│   └── base.py           # BaseAdmin, ReadOnlyAdmin, AuditableAdmin
├── mixins/
│   ├── __init__.py
│   ├── accountability.py # GDPR/Data protection
│   ├── notifiable.py     # Change notifications
│   ├── searchable.py     # Granular search
│   ├── trashable.py      # Soft delete with retention
│   ├── views.py          # View access mixins
│   └── visibility.py     # Access control
├── models/
│   ├── __init__.py
│   ├── base.py           # BaseModel
│   └── audit.py          # AuditLog
├── services/
│   ├── __init__.py
│   └── base.py           # BaseService
├── views/
│   ├── __init__.py
│   ├── base.py           # BaseView, BaseListView, etc.
│   └── core_views.py     # Review, sitemap views
├── landing_models.py
├── urls.py
└── utils.py
```

---

## Model Mixins

### 1. AccountabilityMixin (GDPR/Data Protection)

```python
class Customer(AccountabilityMixin, BaseModel):
    GDPR_FIELDS = ['email', 'phone', 'address']  # Fields to anonymize
    RETENTION_DAYS = 365 * 7  # 7 years retention
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
```

**Features:**
- `created_by`, `modified_by` tracking
- Consent recording with IP and timestamp
- Data anonymization (right to be forgotten)
- Data retention policies
- Data export (portability)

**Methods:**
- `record_consent(ip_address)` - Record data processing consent
- `revoke_consent()` - Revoke consent
- `anonymize(user)` - Anonymize PII fields
- `set_retention(days)` - Set retention period
- `export_data()` - Export all data for portability

---

### 2. NotifiableMixin (Change Notifications)

```python
class Policy(NotifiableMixin, BaseModel):
    NOTIFY_ON = ['create', 'update', 'status_change']
    NOTIFY_CHANNELS = ['email', 'in_app']
    NOTIFY_FIELDS = ['status', 'premium_amount']  # Only notify on these changes
    
    def get_notification_recipients(self):
        return [self.customer]
```

**Features:**
- Configurable notification triggers
- Multiple channels (email, SMS, push, in-app)
- Watcher/subscription system
- Notification cooldown
- Field-specific change notifications

**Methods:**
- `notify(action, changed_fields, actor)` - Send notifications
- `add_watcher(user)` / `remove_watcher(user)` - Manage watchers
- `should_notify(action, changed_fields)` - Check notification rules

---

### 3. SearchableMixin (Granular Search)

```python
class Customer(SearchableMixin, BaseModel):
    SEARCH_FIELDS = ['first_name', 'last_name', 'email', 'phone']
    SEARCH_WEIGHTS = {'email': 3, 'phone': 2, 'first_name': 1}
    SEARCH_RESULT_FIELDS = ['id', 'first_name', 'last_name', 'email']
    SEARCH_TITLE_FIELD = 'full_name'
    SEARCH_ICON = 'user'
```

**Features:**
- Configurable search fields per model
- Weighted search results (ranking)
- Custom result field selection
- Search suggestions/autocomplete
- URL generation for results

**Methods:**
- `Model.search(query, queryset, limit)` - Basic search
- `Model.weighted_search(query)` - Search with ranking
- `Model.search_suggestions(query)` - Autocomplete
- `obj.to_search_result()` - Format as result dict

---

### 4. TrashableMixin (Soft Delete with Retention)

```python
class Document(TrashableMixin, BaseModel):
    TRASH_RETENTION_DAYS = 30  # Keep in trash for 30 days
    ALLOW_PERMANENT_DELETE = True
```

**Features:**
- Move to trash instead of delete
- Configurable retention period
- Automatic permanent deletion after retention
- Custom managers for filtering
- Restore functionality

**Methods:**
- `obj.trash(user, reason)` - Move to trash
- `obj.restore_from_trash()` - Restore
- `Model.empty_expired_trash()` - Clean up expired
- `Model.objects.only_trashed()` - Get trashed items
- `Model.objects.with_trashed()` - Include trashed

---

### 5. VisibilityMixin (Access Control)

```python
class Document(VisibilityMixin, BaseModel):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('internal', 'Internal Only'),
        ('restricted', 'Restricted'),
    ]
    DEFAULT_VISIBILITY = 'private'
```

**Features:**
- Public/Private/Internal/Restricted levels
- Owner-based access
- User whitelist for restricted items
- Group-based access control
- Publish/Draft status

**Methods:**
- `obj.is_visible_to(user)` - Check visibility
- `obj.can_edit(user)` / `obj.can_delete(user)`
- `obj.make_public()` / `obj.make_private()`
- `obj.make_restricted(users, groups)`
- `obj.publish()` / `obj.unpublish()`
- `Model.objects.visible_to(user)` - Filter by visibility

---

## Base Classes

### BaseModel

```python
from apps.core.models import BaseModel

class MyModel(BaseModel):
    name = models.CharField(max_length=100)
```

**Provides:**
- `created_at` - Auto-set creation timestamp
- `updated_at` - Auto-updated on save
- `is_active` - Soft delete flag
- `soft_delete()` / `restore()` methods

---

### BaseService

```python
from apps.core.services import BaseService

class UserService(BaseService):
    model = User
    select_related = ['profile']
    
    def create_user(self, email, password, **kwargs):
        user = self.create(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user
```

**Provides:**
- Standardized CRUD operations
- Query optimization (select_related, prefetch_related)
- Pagination support
- Audit logging integration
- Error handling with custom exceptions
- Transaction management

---

### BaseAdmin

```python
from apps.core.admin import BaseAdmin

@admin.register(MyModel)
class MyModelAdmin(BaseAdmin):
    list_display = ['name', 'is_active_badge', 'created_at']
    list_select_related = ['owner']
```

**Provides:**
- Common actions (activate, deactivate, export CSV)
- Status badge helpers
- Query optimization
- Automatic readonly timestamps
- User tracking on save

---

### BaseView

```python
from apps.core.views import BaseListView, BaseCreateView

class CustomerListView(BaseListView):
    model = Customer
    search_fields = ['name', 'email']
    page_title = 'Customers'

class CustomerCreateView(BaseCreateView):
    model = Customer
    success_message = 'Customer created successfully.'
```

**Provides:**
- Common context data (page_title, breadcrumbs)
- Search and pagination
- Message handling
- Audit logging
- User tracking on create/update
- Soft delete support

---

## View Mixins

```python
from apps.core.mixins import (
    CustomerRequiredMixin,
    AgentRequiredMixin,
    StaffRequiredMixin,
    AdminRequiredMixin,
    OwnerRequiredMixin,
)

class MyProtectedView(StaffRequiredMixin, BaseTemplateView):
    template_name = 'protected.html'
```

---

## Usage Example

```python
from django.db import models
from apps.core.models import BaseModel
from apps.core.mixins import (
    AccountabilityMixin,
    NotifiableMixin,
    SearchableMixin,
    TrashableMixin,
    VisibilityMixin,
)

class Document(
    AccountabilityMixin,
    NotifiableMixin,
    SearchableMixin,
    TrashableMixin,
    VisibilityMixin,
    BaseModel
):
    """
    A fully-featured document model with:
    - GDPR compliance
    - Change notifications
    - Granular search
    - Soft delete with retention
    - Access control
    """
    
    # GDPR
    GDPR_FIELDS = ['title', 'content']
    RETENTION_DAYS = 365 * 5
    
    # Notifications
    NOTIFY_ON = ['create', 'update']
    NOTIFY_CHANNELS = ['email', 'in_app']
    
    # Search
    SEARCH_FIELDS = ['title', 'content']
    SEARCH_TITLE_FIELD = 'title'
    
    # Trash
    TRASH_RETENTION_DAYS = 30
    
    # Visibility
    DEFAULT_VISIBILITY = 'private'
    
    title = models.CharField(max_length=200)
    content = models.TextField()
```

---

## Verification

All Django checks pass with 0 issues:

```
System check identified no issues (0 silenced).
```
