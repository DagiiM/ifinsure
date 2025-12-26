"""
Invoice model.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import BaseModel


class Invoice(BaseModel):
    """Invoices for policy payments."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True, blank=True)
    
    # Relationships
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.PROTECT,
        related_name='invoices',
        null=True,
        blank=True
    )
    
    # Status and dates
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    issued_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    
    # Financial
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Details
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-issued_date']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['due_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
        super().save(*args, **kwargs)
    
    def _generate_invoice_number(self):
        """Generate unique invoice number."""
        prefix = f"INV-{timezone.now().strftime('%Y%m')}"
        last = Invoice.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        if last:
            seq = int(last.invoice_number.split('-')[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:05d}"
    
    @property
    def balance(self):
        """Remaining balance to pay."""
        return self.amount - self.paid_amount
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        if self.status in ['paid', 'cancelled']:
            return False
        return self.due_date < timezone.now().date()
    
    @property
    def days_overdue(self):
        """Days overdue (negative if not due yet)."""
        delta = timezone.now().date() - self.due_date
        return delta.days
    
    def update_status(self):
        """Update status based on payments and due date."""
        if self.paid_amount >= self.amount:
            self.status = 'paid'
        elif self.paid_amount > 0:
            self.status = 'partial'
        elif self.is_overdue:
            self.status = 'overdue'
        else:
            self.status = 'pending'
        self.save(update_fields=['status', 'updated_at'])
