"""
Claims admin configuration.
"""
from django.contrib import admin
from apps.claims.models import Claim, ClaimDocument, ClaimNote, ClaimStatusHistory


class ClaimDocumentInline(admin.TabularInline):
    model = ClaimDocument
    extra = 0
    readonly_fields = ['created_by', 'created_at']


class ClaimNoteInline(admin.TabularInline):
    model = ClaimNote
    extra = 0
    readonly_fields = ['created_by', 'created_at']


class ClaimStatusHistoryInline(admin.TabularInline):
    model = ClaimStatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'created_by', 'created_at', 'notes']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = [
        'claim_number', 'claimant', 'policy', 'status', 'priority',
        'claimed_amount', 'approved_amount', 'incident_date', 'created_at'
    ]
    list_filter = ['status', 'priority', 'policy__product__category', 'created_at']
    search_fields = [
        'claim_number', 'claimant__email', 'claimant__first_name',
        'claimant__last_name', 'policy__policy_number'
    ]
    raw_id_fields = ['policy', 'claimant', 'assigned_adjuster', 'reviewed_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    inlines = [ClaimDocumentInline, ClaimNoteInline, ClaimStatusHistoryInline]
    
    fieldsets = (
        (None, {'fields': ('claim_number', 'status', 'priority', 'is_active')}),
        ('Parties', {'fields': ('policy', 'claimant', 'assigned_adjuster')}),
        ('Incident', {'fields': (
            'incident_date', 'incident_time', 'incident_location', 'incident_description'
        )}),
        ('Financial', {'fields': ('claimed_amount', 'approved_amount', 'paid_amount')}),
        ('Review', {'fields': (
            'submitted_at', 'reviewed_at', 'reviewed_by',
            'rejection_reason', 'adjuster_notes'
        )}),
    )
    
    readonly_fields = ['claim_number', 'submitted_at', 'reviewed_at']


@admin.register(ClaimDocument)
class ClaimDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'claim', 'document_type', 'created_by', 'created_at']
    list_filter = ['document_type', 'created_at']
    search_fields = ['title', 'claim__claim_number']
    raw_id_fields = ['claim', 'created_by']

