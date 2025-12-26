"""
Trash forms.
"""
from django import forms


class TrashFilterForm(forms.Form):
    """Form for filtering trash items."""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search trash...',
        })
    )
    
    type = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, *args, available_models=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if available_models:
            self.fields['type'].choices = [
                (m['model_name'], m['model_verbose_name'] or m['model_name'])
                for m in available_models
            ]


class ConfirmActionForm(forms.Form):
    """Form for confirming dangerous actions."""
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I understand this action cannot be undone'
    )
