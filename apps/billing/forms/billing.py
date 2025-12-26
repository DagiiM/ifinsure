"""
Billing forms.
"""
from django import forms
from decimal import Decimal
from apps.billing.models import Invoice, Payment


class InvoiceCreateForm(forms.ModelForm):
    """Form for creating invoices (staff only)."""
    
    class Meta:
        model = Invoice
        fields = ['customer', 'policy', 'amount', 'due_date', 'description']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'policy': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Invoice amount',
                'min': '0.01',
                'step': '0.01'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Invoice description...'
            }),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be positive')
        return amount


class PaymentRecordForm(forms.ModelForm):
    """Form for recording payments."""
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Payment amount',
                'min': '0.01',
                'step': '0.01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Transaction reference (optional)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Payment notes...'
            }),
        }
    
    def __init__(self, invoice=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        if invoice:
            self.fields['amount'].widget.attrs['max'] = str(invoice.balance)
            self.fields['amount'].widget.attrs['placeholder'] = f'Max: {invoice.balance}'
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be positive')
        if self.invoice and amount > self.invoice.balance:
            raise forms.ValidationError(f'Amount exceeds balance ({self.invoice.balance})')
        return amount


class InvoiceFilterForm(forms.Form):
    """Form for filtering invoices."""
    STATUS_CHOICES = [('', 'All Statuses')] + list(Invoice.STATUS_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by invoice number...'
        })
    )
    overdue_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
