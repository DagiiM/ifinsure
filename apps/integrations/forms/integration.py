from django import forms
from apps.integrations.models import IntegrationConfig, IntegrationProvider


class IntegrationConfigForm(forms.ModelForm):
    """Form for creating/editing integration configurations"""
    
    class Meta:
        model = IntegrationConfig
        fields = ['name', 'environment', 'is_enabled', 'is_primary']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Production M-Pesa'
            }),
            'environment': forms.Select(attrs={'class': 'form-control'}),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, provider=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = provider
        
        # Dynamically add credential fields based on provider schema
        if provider and provider.config_schema:
            for field_name, field_config in provider.config_schema.items():
                field_type = field_config.get('type', 'text')
                required = field_config.get('required', False)
                
                if field_type == 'password':
                    widget = forms.PasswordInput(attrs={
                        'class': 'form-control',
                        'placeholder': field_config.get('placeholder', ''),
                        'autocomplete': 'new-password'
                    })
                    self.fields[f'cred_{field_name}'] = forms.CharField(
                        label=field_config.get('label', field_name),
                        required=required,
                        widget=widget,
                        help_text=field_config.get('help_text', '')
                    )
                else:
                    self.fields[f'cred_{field_name}'] = forms.CharField(
                        label=field_config.get('label', field_name),
                        required=required,
                        widget=forms.TextInput(attrs={
                            'class': 'form-control',
                            'placeholder': field_config.get('placeholder', '')
                        }),
                        help_text=field_config.get('help_text', '')
                    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Collect credentials
        credentials = {}
        if self.provider and self.provider.config_schema:
            for field_name in self.provider.config_schema.keys():
                cred_value = cleaned_data.get(f'cred_{field_name}')
                if cred_value:
                    credentials[field_name] = cred_value
        
        cleaned_data['credentials'] = credentials
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.provider = self.provider
        instance.credentials = self.cleaned_data.get('credentials', {})
        
        if commit:
            instance.save()
        return instance


class IntegrationFilterForm(forms.Form):
    """Form for filtering integration logs"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    DATE_RANGE_CHOICES = [
        ('today', 'Today'),
        ('week', 'Last 7 days'),
        ('month', 'Last 30 days'),
    ]
    
    provider = forms.ModelChoiceField(
        queryset=IntegrationProvider.objects.filter(is_available=True),
        required=False,
        empty_label='All Providers',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        required=False,
        initial='week',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class WebhookTestForm(forms.Form):
    """Form for testing webhook payloads"""
    
    payload = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': '{"event": "payment.completed", "data": {...}}'
        }),
        help_text='Enter JSON payload to test'
    )
    
    def clean_payload(self):
        import json
        payload = self.cleaned_data['payload']
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON payload')
