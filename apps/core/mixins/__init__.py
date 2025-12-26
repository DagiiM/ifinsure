"""
Core mixins package.

Provides reusable mixins for:
- Models: AccountabilityMixin, NotifiableMixin, SearchableMixin, TrashableMixin, VisibilityMixin
- Views: CustomerRequiredMixin, AgentRequiredMixin, StaffRequiredMixin, etc.
"""
# Model Mixins
from .accountability import AccountabilityMixin
from .notifiable import NotifiableMixin
from .searchable import SearchableMixin
from .trashable import TrashableMixin, TrashableManager
from .visibility import VisibilityMixin, VisibilityManager

# View Mixins
from .views import (
    MessageMixin,
    CustomerRequiredMixin,
    AgentRequiredMixin,
    StaffRequiredMixin,
    AdminRequiredMixin,
    OwnerRequiredMixin,
)

__all__ = [
    # Model Mixins
    'AccountabilityMixin',
    'NotifiableMixin',
    'SearchableMixin',
    'TrashableMixin',
    'VisibilityMixin',
    
    # Managers
    'TrashableManager',
    'VisibilityManager',
    
    # View Mixins
    'MessageMixin',
    'CustomerRequiredMixin',
    'AgentRequiredMixin',
    'StaffRequiredMixin',
    'AdminRequiredMixin',
    'OwnerRequiredMixin',
]
