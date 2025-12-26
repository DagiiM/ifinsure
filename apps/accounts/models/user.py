"""
User and Profile models.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from apps.core.models import BaseModel


class UserManager(BaseUserManager):
    """Custom user manager using email as username."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with email as username.
    Supports different user types: customer, agent, staff, admin.
    """
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('staff', 'Staff'),
        ('admin', 'Administrator'),
    ]
    
    # Remove username field, use email instead
    username = None
    email = models.EmailField('Email Address', unique=True)
    
    # User type for role-based access
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer',
        db_index=True
    )
    
    # Additional fields
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Kenya')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.get_full_name() or self.email
    
    def get_full_name(self):
        """Return first_name and last_name with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name if full_name else self.email.split('@')[0]
    
    def get_short_name(self):
        """Return first name or email prefix."""
        return self.first_name or self.email.split('@')[0]
    
    @property
    def is_customer(self):
        """Check if user is a customer."""
        return self.user_type == 'customer'
    
    @property
    def is_agent(self):
        """Check if user is an agent."""
        return self.user_type == 'agent'
    
    @property
    def is_staff_member(self):
        """Check if user is staff (not Django's is_staff)."""
        return self.user_type == 'staff'
    
    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.user_type == 'admin' or self.is_superuser
    
    @property
    def initials(self):
        """Get user initials for avatar."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.email[0:2].upper()


class Profile(BaseModel):
    """
    Extended user profile information.
    Linked one-to-one with User model.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True
    )
    id_type = models.CharField(
        max_length=50,
        choices=[
            ('national_id', 'National ID'),
            ('passport', 'Passport'),
            ('driving_license', 'Driving License'),
        ],
        blank=True
    )
    id_number = models.CharField(max_length=50, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    annual_income = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True, help_text='Internal notes about this user')
    
    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
    
    def __str__(self):
        return f"Profile: {self.user.email}"
