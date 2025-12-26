from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.db.models import Q
from django.contrib import messages

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseListView, BaseDetailView, BaseCreateView, BaseUpdateView
)
from apps.core.mixins import CustomerRequiredMixin, StaffRequiredMixin
from .models import Claim, ClaimDocument, ClaimNote
from .forms import (
    ClaimCreateForm, ClaimUpdateForm, ClaimReviewForm,
    ClaimDocumentForm, ClaimNoteForm, ClaimFilterForm
)
from .services import ClaimService


# Customer Views
class ClaimListView(CustomerRequiredMixin, BaseListView):
    """List claims for the current customer."""
    model = Claim
    template_name = 'claims/list.html'
    context_object_name = 'claims'
    page_title = 'My Claims'
    
    def get_queryset(self):
        qs = super().get_queryset().filter(
            claimant=self.request.user,
            is_active=True
        ).select_related('policy', 'policy__product')
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ClaimFilterForm(self.request.GET)
        context['status_counts'] = {
            'pending': Claim.objects.filter(
                claimant=self.request.user,
                status__in=['submitted', 'under_review', 'investigating']
            ).count(),
            'approved': Claim.objects.filter(
                claimant=self.request.user,
                status__in=['approved', 'partially_approved']
            ).count(),
            'paid': Claim.objects.filter(
                claimant=self.request.user,
                status='paid'
            ).count(),
        }
        return context


class ClaimDetailView(CustomerRequiredMixin, BaseDetailView):
    """View claim details."""
    model = Claim
    template_name = 'claims/detail.html'
    context_object_name = 'claim'
    
    def get_queryset(self):
        return Claim.objects.filter(
            claimant=self.request.user
        ).select_related('policy', 'policy__product', 'assigned_adjuster')
    
    def get_page_title(self):
        return f"Claim: {self.object.claim_number}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documents'] = self.object.documents.all()
        context['notes'] = self.object.notes.filter(is_internal=False)
        context['status_history'] = self.object.status_history.all()[:10]
        context['document_form'] = ClaimDocumentForm()
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle claim submission and document upload."""
        claim = self.get_object()
        claim_service = self.get_service(ClaimService)
        
        if 'submit' in request.POST and claim.status == 'draft':
            try:
                claim_service.submit_claim(claim)
                messages.success(request, 'Claim submitted successfully!')
            except ValueError as e:
                messages.error(request, str(e))
        
        elif 'upload_document' in request.POST:
            form = ClaimDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save(commit=False)
                doc.claim = claim
                doc.uploaded_by = request.user
                doc.save()
                messages.success(request, 'Document uploaded successfully.')
            else:
                messages.error(request, 'Error uploading document.')
        
        return redirect('claims:detail', pk=claim.pk)


class ClaimCreateView(CustomerRequiredMixin, BaseCreateView):
    """
    Create new claim.
    Uses ClaimService for claim creation with validation and audit logging.
    """
    model = Claim
    form_class = ClaimCreateForm
    template_name = 'claims/create.html'
    success_message = 'Claim created as draft. Add documents and submit when ready.'
    page_title = 'File a Claim'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        claim_service = self.get_service(ClaimService)
        try:
            # Use ClaimService for claim creation
            self.object = claim_service.create_claim(
                claimant=self.request.user,
                policy=form.cleaned_data.get('policy'),
                incident_date=form.cleaned_data.get('incident_date'),
                incident_description=form.cleaned_data.get('incident_description', ''),
                claimed_amount=form.cleaned_data.get('claimed_amount'),
                claim_type=form.cleaned_data.get('claim_type', 'general'),
                incident_location=form.cleaned_data.get('incident_location', '')
            )
            messages.success(self.request, self.success_message)
            return redirect(self.get_success_url())
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('claims:detail', kwargs={'pk': self.object.pk})


class ClaimUpdateView(CustomerRequiredMixin, BaseUpdateView):
    """Update claim (draft only)."""
    model = Claim
    form_class = ClaimUpdateForm
    template_name = 'claims/edit.html'
    success_message = 'Claim updated successfully.'
    page_title = 'Edit Claim'
    
    def get_queryset(self):
        return Claim.objects.filter(
            claimant=self.request.user,
            status='draft'
        )
    
    def get_success_url(self):
        return reverse_lazy('claims:detail', kwargs={'pk': self.object.pk})


# Staff/Agent Views
class StaffClaimListView(StaffRequiredMixin, BaseListView):
    """List claims for staff review."""
    model = Claim
    template_name = 'claims/staff/list.html'
    context_object_name = 'claims'
    page_title = 'Claim Review'
    search_fields = ['claim_number', 'policy__policy_number', 'claimant__email']
    
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(assigned_adjuster=self.request.user) |
                Q(assigned_adjuster__isnull=True)
            )
        
        # Additional filters
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        
        return qs.select_related('policy', 'claimant', 'assigned_adjuster')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ClaimFilterForm(self.request.GET)
        claim_service = self.get_service(ClaimService)
        context['statistics'] = claim_service.get_claim_statistics()
        return context


class StaffClaimDetailView(StaffRequiredMixin, BaseDetailView):
    """Staff claim detail and review view."""
    model = Claim
    template_name = 'claims/staff/detail.html'
    context_object_name = 'claim'
    
    def get_queryset(self):
        return Claim.objects.filter(is_active=True).select_related(
            'policy', 'policy__product', 'claimant', 'assigned_adjuster', 'reviewed_by'
        )
    
    def get_page_title(self):
        return f"Review Claim: {self.object.claim_number}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documents'] = self.object.documents.all()
        context['notes'] = self.object.notes.all()
        context['status_history'] = self.object.status_history.all()
        context['review_form'] = ClaimReviewForm()
        context['note_form'] = ClaimNoteForm()
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle review actions and notes."""
        claim = self.get_object()
        claim_service = self.get_service(ClaimService)
        
        if 'review' in request.POST:
            form = ClaimReviewForm(request.POST)
            if form.is_valid():
                action = form.cleaned_data['action']
                notes = form.cleaned_data['notes']
                
                try:
                    if action == 'approve':
                        approved_amount = form.cleaned_data['approved_amount']
                        claim_service.approve_claim(claim, approved_amount, notes)
                        messages.success(request, 'Claim approved successfully.')
                    else:
                        claim_service.reject_claim(claim, notes)
                        messages.success(request, 'Claim rejected.')
                    
                    return redirect('claims:staff_list')
                except ValueError as e:
                    messages.error(request, str(e))
        
        elif 'add_note' in request.POST:
            form = ClaimNoteForm(request.POST)
            if form.is_valid():
                note = form.save(commit=False)
                note.claim = claim
                note.author = request.user
                note.save()
                messages.success(request, 'Note added.')
        
        elif 'assign_to_me' in request.POST:
            try:
                claim_service.assign_adjuster(claim, request.user)
                messages.success(request, 'Claim assigned to you.')
            except ValueError as e:
                messages.error(request, str(e))
        
        elif 'mark_paid' in request.POST:
            try:
                claim_service.mark_paid(claim, claim.approved_amount)
                messages.success(request, 'Claim marked as paid.')
            except ValueError as e:
                messages.error(request, str(e))
        
        elif 'close' in request.POST:
            try:
                claim_service.close_claim(claim)
                messages.success(request, 'Claim closed.')
            except ValueError as e:
                messages.error(request, str(e))
        
        return redirect('claims:staff_detail', pk=claim.pk)
