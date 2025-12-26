from django.db import transaction
from django.contrib.auth import get_user_model
from apps.core.services.base import BaseService, service_action

User = get_user_model()


class AccountService(BaseService):
    """Business logic for user account operations."""
    
    model = User
    
    @service_action(audit=True)
    def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        user_type: str = 'customer',
        phone: str = '',
        **extra_fields
    ):
        """
        Create a new user account.
        """
        if not email:
            raise ValueError('Email is required')
        if not password:
            raise ValueError('Password is required')
        
        email = email.lower().strip()
        
        # Check if email already exists
        if self.model.objects.filter(email=email).exists():
            raise ValueError(f'User with email {email} already exists')
        
        user = self.model.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            user_type=user_type,
            phone=phone,
            **extra_fields
        )
        
        self._log_action('create', instance=user, details={'event': 'User registration', 'user_type': user_type})
        
        return user
    
    @service_action(audit=True)
    def update_user(self, user, **fields):
        """
        Update user account fields.
        """
        allowed_fields = [
            'first_name', 'last_name', 'phone', 'date_of_birth',
            'address', 'city', 'country'
        ]
        
        update_data = {k: v for k, v in fields.items() if k in allowed_fields}
        return self.update(user, **update_data)
    
    @service_action(audit=True)
    def update_profile(self, user, **fields):
        """
        Update user profile fields.
        """
        profile = user.profile
        allowed_fields = [
            'avatar', 'id_type', 'id_number', 'occupation', 'employer',
            'annual_income', 'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'notes'
        ]
        
        update_data = {k: v for k, v in fields.items() if k in allowed_fields}
        
        # profile is not this service's primary model, but we can still use self.update if we want
        # or just save it directly. self.update takes an instance and kwargs.
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        profile.save()
        
        self._log_action('update', instance=profile, details={'updated_fields': list(update_data.keys())})
        
        return profile
    
    @service_action(audit=True)
    def change_password(self, user, new_password):
        """
        Change user password.
        """
        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'])
        
        self._log_action('update', instance=user, details={'event': 'Password changed'})
        
        return user
    
    @service_action(audit=True)
    def change_user_type(self, user, new_type):
        """
        Change user type/role.
        """
        valid_types = ['customer', 'agent', 'staff', 'admin']
        if new_type not in valid_types:
            raise ValueError(f'Invalid user type: {new_type}. Must be one of {valid_types}')
        
        old_type = user.user_type
        if old_type == new_type:
            return user
        
        user.user_type = new_type
        # Set is_staff flag for agent/staff/admin
        user.is_staff = new_type in ['agent', 'staff', 'admin']
        
        user.save(update_fields=['user_type', 'is_staff', 'updated_at'])
        
        self._log_action('update', instance=user, changes={'user_type': {'from': old_type, 'to': new_type}})
        
        return user
    
    @service_action(audit=True)
    def deactivate_user(self, user, reason: str = ''):
        """
        Deactivate a user account.
        """
        user.is_active = False
        user.save(update_fields=['is_active', 'updated_at'])
        
        self._log_action('update', instance=user, changes={'is_active': False, 'reason': reason})
        
        return user
    
    @service_action(audit=True)
    def activate_user(self, user):
        """
        Activate a user account.
        """
        user.is_active = True
        user.save(update_fields=['is_active', 'updated_at'])
        
        self._log_action('update', instance=user, changes={'is_active': True})
        
        return user
    
    def log_login(self, user):
        """Log user login event."""
        # Note: can't easily pass request here without changing signature significantly
        # but BaseService._log_action doesn't take request yet (it gets context from _current_user)
        self._log_action('login', instance=user)
    
    def log_logout(self, user):
        """Log user logout event."""
        self._log_action('logout', instance=user)
    
    def get_user_by_email(self, email: str):
        """Get user by email address."""
        try:
            return self.model.objects.get(email=email.lower().strip())
        except self.model.DoesNotExist:
            return None
    
    def get_users_by_type(self, user_type: str, active_only: bool = True):
        """Get all users of a specific type."""
        qs = self.model.objects.filter(user_type=user_type)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs
