"""
Notification forms.
"""
from django import forms
from ..models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    """Form for editing notification preferences."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
            'notify_policy_created', 'notify_policy_updated',
            'notify_policy_expiring', 'notify_policy_expired',
            'notify_claim_submitted', 'notify_claim_updated',
            'notify_claim_approved', 'notify_claim_rejected',
            'notify_payment_due', 'notify_payment_received', 'notify_payment_overdue',
            'notify_system_updates', 'notify_security_alerts', 'notify_promotions',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'email_digest_enabled', 'email_digest_frequency',
        ]
        widgets = {
            'quiet_hours_start': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'quiet_hours_end': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'email_digest_frequency': forms.Select(
                attrs={'class': 'form-select'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Group fields for display
        self.channel_fields = ['email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled']
        self.policy_fields = ['notify_policy_created', 'notify_policy_updated', 
                             'notify_policy_expiring', 'notify_policy_expired']
        self.claim_fields = ['notify_claim_submitted', 'notify_claim_updated',
                            'notify_claim_approved', 'notify_claim_rejected']
        self.payment_fields = ['notify_payment_due', 'notify_payment_received', 'notify_payment_overdue']
        self.system_fields = ['notify_system_updates', 'notify_security_alerts', 'notify_promotions']
        
        # Add CSS classes to all boolean fields
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.widget.attrs['class'] = 'form-check-input'
