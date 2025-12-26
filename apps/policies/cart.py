"""
Cart services for managing insurance product cart.
Uses session-based storage for anonymous users.
"""
from decimal import Decimal
from typing import List, Dict, Optional
from django.contrib.sessions.backends.base import SessionBase

from apps.policies.models import InsuranceProduct


CART_SESSION_KEY = 'insurance_cart'


class Cart:
    """
    Session-based shopping cart for insurance products.
    Works for both anonymous and authenticated users.
    """
    
    def __init__(self, session: SessionBase):
        self.session = session
        cart = session.get(CART_SESSION_KEY)
        if not cart:
            cart = {}
        self.cart = cart
    
    def save(self):
        """Save cart to session."""
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True
    
    def add(self, product: InsuranceProduct, coverage_amount: Decimal = None, 
            term_months: int = 12, payment_frequency: str = 'monthly') -> dict:
        """
        Add a product to the cart.
        Each product can only be added once (insurance-specific).
        """
        product_id = str(product.pk)
        
        if coverage_amount is None:
            coverage_amount = product.min_coverage
        
        # Calculate premium based on coverage
        premium = product.calculate_premium(coverage_amount)
        
        self.cart[product_id] = {
            'product_id': str(product.pk),
            'product_name': product.name,
            'product_code': product.code,
            'category': product.category.name if product.category else '',
            'coverage_amount': str(coverage_amount),
            'term_months': term_months,
            'payment_frequency': payment_frequency,
            'premium': str(premium),
            'base_premium': str(product.base_premium),
        }
        self.save()
        return self.cart[product_id]
    
    def update(self, product_id, coverage_amount: Decimal = None,
               term_months: int = None, payment_frequency: str = None) -> Optional[dict]:
        """Update an item in the cart."""
        product_id_str = str(product_id)
        
        if product_id_str not in self.cart:
            return None
        
        item = self.cart[product_id_str]
        
        # Get the product to recalculate premium if coverage changed
        if coverage_amount is not None:
            try:
                product = InsuranceProduct.objects.get(pk=product_id)
                item['coverage_amount'] = str(coverage_amount)
                item['premium'] = str(product.calculate_premium(coverage_amount))
            except InsuranceProduct.DoesNotExist:
                pass
        
        if term_months is not None:
            item['term_months'] = term_months
        
        if payment_frequency is not None:
            item['payment_frequency'] = payment_frequency
        
        self.save()
        return item
    
    def remove(self, product_id) -> bool:
        """Remove a product from the cart."""
        product_id_str = str(product_id)
        if product_id_str in self.cart:
            del self.cart[product_id_str]
            self.save()
            return True
        return False
    
    def clear(self):
        """Clear all items from the cart."""
        self.cart = {}
        self.save()
    
    def get_item(self, product_id) -> Optional[dict]:
        """Get a single item from the cart."""
        return self.cart.get(str(product_id))
    
    def __iter__(self):
        """Iterate over cart items with product objects."""
        product_ids = list(self.cart.keys())
        products = InsuranceProduct.objects.filter(pk__in=product_ids)
        products_map = {str(p.pk): p for p in products}
        
        for product_id, item in self.cart.items():
            item = item.copy()
            item['product'] = products_map.get(product_id)
            item['coverage_amount'] = Decimal(item['coverage_amount'])
            item['premium'] = Decimal(item['premium'])
            item['base_premium'] = Decimal(item['base_premium'])
            yield item
    
    def __len__(self):
        """Return number of items in cart."""
        return len(self.cart)
    
    def get_total_premium(self) -> Decimal:
        """Calculate total monthly premium for all items."""
        total = Decimal('0')
        for item in self:
            total += item['premium']
        return total
    
    def get_total_coverage(self) -> Decimal:
        """Calculate total coverage amount for all items."""
        total = Decimal('0')
        for item in self:
            total += item['coverage_amount']
        return total
    
    def is_empty(self) -> bool:
        """Check if cart is empty."""
        return len(self.cart) == 0
    
    def has_product(self, product_id) -> bool:
        """Check if product is already in cart."""
        return str(product_id) in self.cart
    
    def to_dict(self) -> Dict:
        """Return cart as dictionary for JSON responses."""
        return {
            'items': list(self),
            'count': len(self),
            'total_premium': str(self.get_total_premium()),
            'total_coverage': str(self.get_total_coverage()),
        }


def get_cart(request) -> Cart:
    """Get or create cart for the current request."""
    return Cart(request.session)
