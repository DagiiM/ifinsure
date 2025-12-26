"""
Claims forms.
"""
from django import forms
from decimal import Decimal
from apps.claims.models import Claim, ClaimDocument, ClaimNote


class ClaimCreateForm(forms.ModelForm):
    """Form for creating a new claim."""
    
    class Meta:
        model = Claim
        fields = [
            'policy', 'incident_date', 'incident_time', 'incident_location',
            'incident_description', 'claimed_amount'
        ]
        widgets = {
            'policy': forms.Select(attrs={'class': 'form-select'}),
            'incident_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'incident_time': forms.TimeInput(attrs={
                'class': 'form-input',
                'type': 'time'
            }),
            'incident_location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Where did the incident occur?'
            }),
            'incident_description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Describe what happened in detail...'
            }),
            'claimed_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Amount you are claiming',
                'min': '1',
                'step': '0.01'
            }),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Limit policies to user's active policies
            self.fields['policy'].queryset = user.policies.filter(
                status='active',
                is_active=True
            )
    
    def clean_claimed_amount(self):
        amount = self.cleaned_data['claimed_amount']
        if amount <= 0:
            raise forms.ValidationError('Claimed amount must be positive')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        policy = cleaned_data.get('policy')
        claimed_amount = cleaned_data.get('claimed_amount')
        
        if policy and claimed_amount:
            if claimed_amount > policy.coverage_amount:
                raise forms.ValidationError(
                    f'Claimed amount cannot exceed policy coverage ({policy.coverage_amount:,.2f})'
                )
        
        return cleaned_data


class ClaimUpdateForm(forms.ModelForm):
    """Form for updating claim details (draft only)."""
    
    class Meta:
        model = Claim
        fields = [
            'incident_date', 'incident_time', 'incident_location',
            'incident_description', 'claimed_amount'
        ]
        widgets = {
            'incident_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'incident_time': forms.TimeInput(attrs={
                'class': 'form-input',
                'type': 'time'
            }),
            'incident_location': forms.TextInput(attrs={'class': 'form-input'}),
            'incident_description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4
            }),
            'claimed_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'step': '0.01'
            }),
        }


class ClaimReviewForm(forms.Form):
    """Form for reviewing claims (approve/reject)."""
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'})
    )
    approved_amount = forms.DecimalField(
        required=False,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Amount to approve',
            'min': '0.01',
            'step': '0.01'
        })
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
        approved_amount = cleaned_data.get('approved_amount')
        notes = cleaned_data.get('notes')
        
        if action == 'approve' and not approved_amount:
            raise forms.ValidationError(
                {'approved_amount': 'Approved amount is required'}
            )
        
        if action == 'reject' and not notes:
            raise forms.ValidationError(
                {'notes': 'Rejection reason is required'}
            )
        
        return cleaned_data


class ClaimDocumentForm(forms.ModelForm):
    """Form for uploading claim documents."""
    
    class Meta:
        model = ClaimDocument
        fields = ['document_type', 'title', 'file', 'description']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Document title'
            }),
            'file': forms.FileInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Optional description...'
            }),
        }


class ClaimNoteForm(forms.ModelForm):
    """Form for adding notes to claims."""
    
    class Meta:
        model = ClaimNote
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Add a note...'
            }),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ClaimFilterForm(forms.Form):
    """Form for filtering claims."""
    STATUS_CHOICES = [('', 'All Statuses')] + list(Claim.STATUS_CHOICES)
    PRIORITY_CHOICES = [('', 'All Priorities')] + list(Claim.PRIORITY_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by claim number or policy...'
        })
    )
