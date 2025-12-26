"""
CRM admin package.
"""
from .admin import (
    InsuranceProviderAdmin,
    ProductCategoryAdmin,
    InsuranceProductAdmin,
    CustomerTagAdmin,
    CustomerAdmin,
    LeadAdmin,
    CommunicationAdmin,
)

__all__ = [
    'InsuranceProviderAdmin',
    'ProductCategoryAdmin',
    'InsuranceProductAdmin',
    'CustomerTagAdmin',
    'CustomerAdmin',
    'LeadAdmin',
    'CommunicationAdmin',
]
