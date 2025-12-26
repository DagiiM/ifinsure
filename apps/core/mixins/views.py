"""
View mixins for access control and common functionality.
Now imported from apps.core.views.base to ensure consistency.
"""
from apps.core.views.base import (
    MessageMixin,
    CustomerRequiredMixin,
    AgentRequiredMixin,
    StaffRequiredMixin,
    AdminRequiredMixin,
    OwnerRequiredMixin,
)
