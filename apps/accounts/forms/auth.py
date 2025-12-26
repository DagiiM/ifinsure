"""
Accounts forms - Authentication and profile forms.
"""
from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
)
from apps.accounts.models import User, Profile


class LoginForm(AuthenticationForm):
    """Custom login form with styled widgets."""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    
    error_messages = {
        'invalid_login': 'Invalid email or password. Please try again.',
        'inactive': 'This account is inactive.',
    }


class RegistrationForm(UserCreationForm):
    """User registration form."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email',
        })
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Phone number',
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        error_messages={'required': 'You must accept the terms and conditions.'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'  # Default to customer
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """Form for updating user basic info."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'address', 'city']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3
            }),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
        }


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating profile extended info."""
    
    class Meta:
        model = Profile
        fields = [
            'id_type', 'id_number', 'occupation', 'employer',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship'
        ]
        widgets = {
            'id_type': forms.Select(attrs={'class': 'form-select'}),
            'id_number': forms.TextInput(attrs={'class': 'form-input'}),
            'occupation': forms.TextInput(attrs={'class': 'form-input'}),
            'employer': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-input'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with styled widgets."""
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current password',
        })
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password',
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
        })
    )
