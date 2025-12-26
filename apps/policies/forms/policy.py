"""
Policies forms.
"""
from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.policies.models import PolicyApplication, InsuranceProduct, Policy


class PolicyApplicationForm(forms.ModelForm):
    """Form for creating policy applications."""
    
    class Meta:
        model = PolicyApplication
        fields = [
            'product', 'requested_coverage', 'requested_term_months',
            'payment_frequency', 'beneficiary_name', 'beneficiary_relationship',
            'beneficiary_phone', 'notes'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'requested_coverage': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter coverage amount',
                'min': '10000',
                'step': '1000',
            }),
            'requested_term_months': forms.Select(
                choices=[(12, '1 Year'), (24, '2 Years'), (36, '3 Years'), 
                         (48, '4 Years'), (60, '5 Years')],
                attrs={'class': 'form-select'}
            ),
            'payment_frequency': forms.Select(attrs={'class': 'form-select'}),
            'beneficiary_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Beneficiary full name'
            }),
            'beneficiary_relationship': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Spouse, Child, Parent'
            }),
            'beneficiary_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Beneficiary phone number'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Any additional information...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = InsuranceProduct.objects.filter(is_active=True)
        self.fields['beneficiary_name'].required = False
        self.fields['beneficiary_relationship'].required = False
        self.fields['beneficiary_phone'].required = False
        self.fields['notes'].required = False
    
    def clean_requested_coverage(self):
        coverage = self.cleaned_data['requested_coverage']
        product = self.cleaned_data.get('product')
        
        if coverage < Decimal('10000'):
            raise forms.ValidationError('Minimum coverage is 10,000')
        
        if product:
            if coverage < product.min_coverage:
                raise forms.ValidationError(
                    f'Minimum coverage for this product is {product.min_coverage:,.2f}'
                )
            if coverage > product.max_coverage:
                raise forms.ValidationError(
                    f'Maximum coverage for this product is {product.max_coverage:,.2f}'
                )
        
        return coverage


class ApplicationReviewForm(forms.Form):
    """Form for reviewing applications (approve/reject)."""
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Review notes or rejection reason...'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        notes = cleaned_data.get('notes')
        
        if action == 'reject' and not notes:
            raise forms.ValidationError(
                {'notes': 'Rejection reason is required'}
            )
        
        return cleaned_data


class PolicyFilterForm(forms.Form):
    """Form for filtering policies."""
    STATUS_CHOICES = [('', 'All Statuses')] + list(Policy.STATUS_CHOICES)
    CATEGORY_CHOICES = [('', 'All Categories')] + list(InsuranceProduct.CATEGORY_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by policy number or customer...'
        })
    )
