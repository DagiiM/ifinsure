from django.db import transaction
from django.utils import timezone
from apps.core.services.base import BaseService, service_action
from apps.crm.models import Customer, Lead, Communication


class CRMService(BaseService):
    """Business logic for CRM operations."""
    
    model = Customer
    
    # ============ CUSTOMER OPERATIONS ============
    
    @service_action(audit=True)
    def create_customer(
        self,
        customer_type: str = 'individual',
        email: str = '',
        phone: str = '',
        first_name: str = '',
        last_name: str = '',
        company_name: str = '',
        **extra_fields
    ) -> Customer:
        """
        Create a new customer record.
        """
        # Validation
        if customer_type == 'individual':
            if not first_name or not last_name:
                raise ValueError('First name and last name are required for individuals')
        elif customer_type == 'corporate':
            if not company_name:
                raise ValueError('Company name is required for corporate customers')
        
        if not email and not phone:
            raise ValueError('Either email or phone is required')
        
        # Check for duplicates
        if email:
            email = email.lower().strip()
            if self.model.objects.filter(email=email).exists():
                raise ValueError(f'Customer with email {email} already exists')
        
        customer = self.create(
            customer_type=customer_type,
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            lifecycle_stage='lead',
            **extra_fields
        )
        
        return customer
    
    @service_action(audit=True)
    def update_customer(self, customer: Customer, **fields) -> Customer:
        """
        Update customer record.
        """
        allowed_fields = [
            'first_name', 'middle_name', 'last_name', 'email', 'phone', 'alt_phone',
            'id_type', 'id_number', 'date_of_birth', 'gender',
            'company_name', 'company_registration', 'kra_pin',
            'address', 'city', 'county', 'country',
            'lifecycle_stage', 'source', 'notes'
        ]
        
        update_data = {k: v for k, v in fields.items() if k in allowed_fields}
        return self.update(customer, **update_data)
    
    @service_action(audit=True)
    def update_lifecycle_stage(self, customer: Customer, new_stage: str) -> Customer:
        """
        Update customer lifecycle stage.
        """
        valid_stages = ['lead', 'prospect', 'customer', 'active', 'inactive', 'churned']
        if new_stage not in valid_stages:
            raise ValueError(f'Invalid lifecycle stage: {new_stage}')
        
        return self.update(customer, lifecycle_stage=new_stage)
    
    def get_customers(self, search: str = None, lifecycle_stage: str = None, customer_type: str = None):
        """Get customers with optional filtering."""
        qs = self.get_queryset().filter(is_active=True)
        
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        if lifecycle_stage:
            qs = qs.filter(lifecycle_stage=lifecycle_stage)
        
        if customer_type:
            qs = qs.filter(customer_type=customer_type)
        
        return qs.order_by('-created_at')
    
    # ============ LEAD OPERATIONS ============
    
    @service_action(audit=True)
    def create_lead(
        self,
        customer: Customer,
        source: str = '',
        product=None,
        notes: str = ''
    ) -> Lead:
        """
        Create a new lead.
        """
        lead = Lead.objects.create(
            customer=customer,
            assigned_to=self._current_user,
            source=source,
            interested_product=product,
            notes=notes,
            status='new'
        )
        
        self._log_action('create', instance=lead, details={'source': source})
        
        return lead
    
    @service_action(audit=True)
    def update_lead_status(self, lead: Lead, new_status: str, notes: str = '') -> Lead:
        """
        Update lead status.
        """
        valid_statuses = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
        if new_status not in valid_statuses:
            raise ValueError(f'Invalid lead status: {new_status}')
        
        old_status = lead.status
        lead.status = new_status
        
        if notes:
            lead.notes = f"{lead.notes}\n[{timezone.now():%Y-%m-%d}] Status → {new_status}: {notes}".strip()
        
        # Set win/loss date
        if new_status == 'won':
            lead.won_date = timezone.now()
        elif new_status == 'lost':
            lead.lost_date = timezone.now()
            lead.lost_reason = notes
        
        lead.save()
        
        self._log_action('update', instance=lead, changes={'status': {'from': old_status, 'to': new_status}})
        
        return lead
    
    @service_action(audit=True)
    def assign_lead(self, lead: Lead, assignee) -> Lead:
        """
        Assign lead to a user.
        """
        old_assignee = lead.assigned_to
        lead.assigned_to = assignee
        lead.save(update_fields=['assigned_to', 'updated_at'])
        
        self._log_action('update', instance=lead, details={
            'assigned_to': {
                'from': str(old_assignee) if old_assignee else None,
                'to': str(assignee)
            }
        })
        
        return lead
    
    def get_leads(
        self,
        assigned_to=None,
        status: str = None,
        search: str = None
    ):
        """Get leads with optional filtering."""
        qs = Lead.objects.filter(is_active=True).select_related('customer', 'assigned_to')
        
        if assigned_to:
            qs = qs.filter(assigned_to=assigned_to)
        
        if status:
            qs = qs.filter(status=status)
        
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(customer__email__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )
        
        return qs.order_by('-created_at')
    
    # ============ COMMUNICATION OPERATIONS ============
    
    @service_action(audit=True)
    def add_communication(
        self,
        customer: Customer,
        communication_type: str,
        direction: str,
        subject: str = '',
        content: str = '',
        lead: Lead = None,
        **extra_fields
    ) -> Communication:
        """
        Record a customer communication.
        """
        communication = Communication.objects.create(
            customer=customer,
            lead=lead,
            communication_type=communication_type,
            direction=direction,
            subject=subject,
            content=content,
            performed_by=self._current_user,
            **extra_fields
        )
        
        # Update customer last contact
        customer.last_contact_date = timezone.now()
        customer.save(update_fields=['last_contact_date'])
        
        self._log_action('create', instance=communication, details={'type': communication_type, 'direction': direction})
        
        return communication
    
    def get_customer_communications(self, customer: Customer, limit: int = None):
        """Get communications for a customer."""
        qs = Communication.objects.filter(
            customer=customer
        ).select_related('performed_by').order_by('-created_at')
        
        if limit:
            qs = qs[:limit]
        
        return qs
    
    # ============ STATISTICS ============
    
    def get_crm_statistics(self):
        """Get CRM statistics for dashboard."""
        from django.db.models import Count
        
        return {
            'total_customers': self.model.objects.filter(is_active=True).count(),
            'active_customers': self.model.objects.filter(
                is_active=True, lifecycle_stage='active'
            ).count(),
            'total_leads': Lead.objects.filter(is_active=True).count(),
            'leads_by_status': dict(
                Lead.objects.filter(is_active=True)
                .values('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
            'conversion_rate': self._calculate_conversion_rate(),
        }
    
    def _calculate_conversion_rate(self):
        """Calculate lead to customer conversion rate."""
        total = Lead.objects.filter(
            is_active=True,
            status__in=['won', 'lost']
        ).count()
        
        if total == 0:
            return 0
        
        won = Lead.objects.filter(is_active=True, status='won').count()
        return round((won / total) * 100, 1)
