"""
Trash tests.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from apps.trash.models import TrashRegistry
from apps.trash.services import TrashService

User = get_user_model()


class TrashRegistryModelTest(TestCase):
    """Test TrashRegistry model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_registry_entry(self):
        """Test creating a trash registry entry."""
        content_type = ContentType.objects.get_for_model(User)
        
        entry = TrashRegistry.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            title='Deleted User',
            model_name='user',
            model_verbose_name='User',
            trashed_by=self.user,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        self.assertEqual(entry.title, 'Deleted User')
        self.assertEqual(entry.trashed_by, self.user)
    
    def test_days_until_expiry(self):
        """Test days until expiry calculation."""
        content_type = ContentType.objects.get_for_model(User)
        
        entry = TrashRegistry.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            title='Test',
            model_name='user',
            expires_at=timezone.now() + timedelta(days=15)
        )
        
        # Should be around 15 days
        self.assertIn(entry.days_until_expiry, [14, 15])
    
    def test_is_expired(self):
        """Test expired check."""
        content_type = ContentType.objects.get_for_model(User)
        
        # Non-expired
        entry = TrashRegistry.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            title='Not expired',
            model_name='user',
            expires_at=timezone.now() + timedelta(days=10)
        )
        self.assertFalse(entry.is_expired)
        
        # Expired
        expired_entry = TrashRegistry.objects.create(
            content_type=content_type,
            object_id=999,
            title='Expired',
            model_name='user',
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(expired_entry.is_expired)
    
    def test_to_dict(self):
        """Test serialization."""
        content_type = ContentType.objects.get_for_model(User)
        
        entry = TrashRegistry.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            title='Test',
            model_name='user',
            trashed_by=self.user,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        data = entry.to_dict()
        
        self.assertEqual(data['title'], 'Test')
        self.assertEqual(data['model'], 'user')
        self.assertFalse(data['is_expired'])


class TrashServiceTest(TestCase):
    """Test TrashService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.service = TrashService(self.user)
    
    def test_get_statistics(self):
        """Test getting trash statistics."""
        content_type = ContentType.objects.get_for_model(User)
        
        # Create some trash entries
        for i in range(3):
            TrashRegistry.objects.create(
                content_type=content_type,
                object_id=i + 100,
                title=f'Item {i}',
                model_name='user',
                trashed_by=self.user,
                expires_at=timezone.now() + timedelta(days=30)
            )
        
        stats = self.service.get_statistics()
        
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['can_restore'], 3)
    
    def test_get_all_trashed(self):
        """Test getting all trashed items."""
        content_type = ContentType.objects.get_for_model(User)
        
        TrashRegistry.objects.create(
            content_type=content_type,
            object_id=100,
            title='My Item',
            model_name='user',
            trashed_by=self.user,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        items = self.service.get_all_trashed()
        
        self.assertEqual(items.count(), 1)
    
    def test_user_only_sees_own_items(self):
        """Test non-admin only sees own trashed items."""
        content_type = ContentType.objects.get_for_model(User)
        
        # Create item by user
        TrashRegistry.objects.create(
            content_type=content_type,
            object_id=100,
            title='User Item',
            model_name='user',
            trashed_by=self.user,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        # Create item by admin
        TrashRegistry.objects.create(
            content_type=content_type,
            object_id=101,
            title='Admin Item',
            model_name='user',
            trashed_by=self.admin,
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        # User should only see their item
        items = self.service.get_all_trashed()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().title, 'User Item')
        
        # Admin should see all
        admin_service = TrashService(self.admin)
        admin_items = admin_service.get_all_trashed()
        self.assertEqual(admin_items.count(), 2)


class TrashViewsTest(TestCase):
    """Test trash views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_trash_list_view(self):
        """Test trash list view."""
        response = self.client.get(reverse('trash:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_trash_api_view(self):
        """Test trash API endpoint."""
        response = self.client.get(
            reverse('trash:api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_trash_statistics_api(self):
        """Test trash statistics API."""
        response = self.client.get(
            reverse('trash:api'),
            {'stats': 'true'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total', data['data'])
