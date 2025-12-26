"""
Search forms.
"""
from django import forms


class GlobalSearchForm(forms.Form):
    """Form for global search."""
    
    q = forms.CharField(
        min_length=2,
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control search-input',
            'placeholder': 'Search...',
            'autocomplete': 'off',
            'autofocus': True,
        })
    )
    
    type = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    def __init__(self, *args, **kwargs):
        available_models = kwargs.pop('available_models', [])
        super().__init__(*args, **kwargs)
        
        # Set choices from registered models
        self.fields['type'].choices = [
            (m['name'], m['verbose_name_plural'])
            for m in available_models
        ]
