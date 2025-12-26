"""
Core models package - base classes and shared models.
"""
from .base import BaseModel, BaseModelManager
from .audit import AuditLog

# For lightweight models that don't need all features
from .simple_base import SimpleBaseModel

__all__ = [
    'BaseModel',
    'BaseModelManager', 
    'SimpleBaseModel',
    'AuditLog',
]

