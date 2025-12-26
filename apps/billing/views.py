from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseDetailView, BaseCreateView
)
from apps.core.mixins import CustomerRequiredMixin, StaffRequiredMixin
from .models import Invoice, Payment
from .forms import InvoiceCreateForm, PaymentRecordForm, InvoiceFilterForm
from .services import BillingService


# Customer Views
class InvoiceListView(CustomerRequiredMixin, BaseListView):
    """List invoices for the current customer."""
    model = Invoice
    template_name = 'billing/invoices.html'
    context_object_name = 'invoices'
    page_title = 'My Invoices'
    
    def get_queryset(self):
        qs = super().get_queryset().filter(
            customer=self.request.user,
            is_active=True
        ).select_related('policy')
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = InvoiceFilterForm(self.request.GET)
        
        # Summary stats
        qs = Invoice.objects.filter(customer=self.request.user, is_active=True)
        context['total_due'] = sum(i.balance for i in qs.filter(status__in=['pending', 'partial', 'overdue']))
        context['overdue_count'] = qs.filter(status='overdue').count()
        return context


class InvoiceDetailView(CustomerRequiredMixin, BaseDetailView):
    """View invoice details."""
    model = Invoice
    template_name = 'billing/invoice_detail.html'
    context_object_name = 'invoice'
    
    def get_queryset(self):
        return Invoice.objects.filter(
            customer=self.request.user
        ).select_related('policy')
    
    def get_page_title(self):
        return f"Invoice: {self.object.invoice_number}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all()
        context['payment_form'] = PaymentRecordForm(invoice=self.object)
        return context


class CustomerPaymentView(CustomerRequiredMixin, BaseCreateView):
    """Record customer payment (simplified for self-service)."""
    model = Payment
    form_class = PaymentRecordForm
    template_name = 'billing/payment.html'
    page_title = 'Make Payment'
    
    def get_invoice(self):
        return get_object_or_404(
            Invoice,
            pk=self.kwargs['invoice_pk'],
            customer=self.request.user,
            status__in=['pending', 'partial', 'overdue']
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['invoice'] = self.get_invoice()
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = self.get_invoice()
        return context
    
    def form_valid(self, form):
        invoice = self.get_invoice()
        billing_service = self.get_service(BillingService)
        
        try:
            billing_service.record_payment(
                invoice=invoice,
                amount=form.cleaned_data['amount'],
                payment_method=form.cleaned_data['payment_method'],
                transaction_id=form.cleaned_data.get('transaction_id', ''),
                notes=form.cleaned_data.get('notes', '')
            )
            messages.success(self.request, 'Payment recorded successfully!')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


# Staff Views
class StaffInvoiceListView(StaffRequiredMixin, BaseListView):
    """List all invoices for staff."""
    model = Invoice
    template_name = 'billing/staff/invoices.html'
    context_object_name = 'invoices'
    page_title = 'Invoice Management'
    search_fields = ['invoice_number', 'customer__email', 'customer__first_name']
    
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        
        # Additional filters
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        overdue = self.request.GET.get('overdue_only')
        if overdue:
            qs = qs.filter(status='overdue')
        
        return qs.select_related('customer', 'policy')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = InvoiceFilterForm(self.request.GET)
        billing_service = self.get_service(BillingService)
        context['statistics'] = billing_service.get_billing_statistics()
        return context


class StaffInvoiceDetailView(StaffRequiredMixin, BaseDetailView):
    """Staff invoice detail view with payment recording."""
    model = Invoice
    template_name = 'billing/staff/invoice_detail.html'
    context_object_name = 'invoice'
    
    def get_queryset(self):
        return Invoice.objects.filter(is_active=True).select_related('customer', 'policy')
    
    def get_page_title(self):
        return f"Invoice Detail: {self.object.invoice_number}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all()
        context['payment_form'] = PaymentRecordForm(invoice=self.object)
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle payment recording and cancellation."""
        invoice = self.get_object()
        billing_service = self.get_service(BillingService)
        
        if 'record_payment' in request.POST:
            form = PaymentRecordForm(invoice=invoice, data=request.POST)
            if form.is_valid():
                try:
                    billing_service.record_payment(
                        invoice=invoice,
                        amount=form.cleaned_data['amount'],
                        payment_method=form.cleaned_data['payment_method'],
                        transaction_id=form.cleaned_data.get('transaction_id', ''),
                        notes=form.cleaned_data.get('notes', '')
                    )
                    messages.success(request, 'Payment recorded successfully!')
                except ValueError as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, 'Invalid payment data.')
        
        elif 'cancel' in request.POST:
            reason = request.POST.get('cancel_reason', '')
            try:
                billing_service.cancel_invoice(invoice, reason)
                messages.success(request, 'Invoice cancelled.')
            except ValueError as e:
                messages.error(request, str(e))
        
        return redirect('billing:staff_invoice_detail', pk=invoice.pk)


class StaffInvoiceCreateView(StaffRequiredMixin, BaseCreateView):
    """
    Create invoice (staff only).
    Uses BillingService for invoice creation with audit logging.
    """
    model = Invoice
    form_class = InvoiceCreateForm
    template_name = 'billing/staff/invoice_create.html'
    success_message = 'Invoice created successfully.'
    page_title = 'Create Invoice'
    
    def form_valid(self, form):
        billing_service = self.get_service(BillingService)
        try:
            # Use BillingService for invoice creation
            self.object = billing_service.create_invoice(
                customer=form.cleaned_data['customer'],
                amount=form.cleaned_data['amount'],
                due_date=form.cleaned_data['due_date'],
                policy=form.cleaned_data.get('policy'),
                description=form.cleaned_data.get('description', '')
            )
            messages.success(self.request, self.success_message)
            return redirect(self.get_success_url())
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
    
    def get_success_url(self):
        return f"/billing/staff/{self.object.pk}/"

