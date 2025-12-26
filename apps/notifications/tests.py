"""
Notification tests.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services import NotificationService

User = get_user_model()


class NotificationModelTest(TestCase):
    """Test Notification model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_notification(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='This is a test message',
            notification_type='info'
        )
        
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.recipient, self.user)
        self.assertFalse(notification.is_read)
    
    def test_mark_as_read(self):
        """Test marking notification as read."""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test message'
        )
        
        self.assertFalse(notification.is_read)
        notification.mark_as_read()
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_archive(self):
        """Test archiving notification."""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test message'
        )
        
        self.assertFalse(notification.is_archived)
        notification.archive()
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_archived)
    
    def test_to_dict(self):
        """Test notification serialization."""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test message',
            notification_type='success'
        )
        
        data = notification.to_dict()
        
        self.assertEqual(data['title'], 'Test')
        self.assertEqual(data['type'], 'success')
        self.assertFalse(data['is_read'])


class NotificationPreferenceTest(TestCase):
    """Test NotificationPreference model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_preferences_created_with_user(self):
        """Test preferences are auto-created when user is created."""
        # Create new user
        new_user = User.objects.create_user(
            email='newuser@example.com',
            password='testpass123'
        )
        
        # Preferences should exist
        self.assertTrue(
            NotificationPreference.objects.filter(user=new_user).exists()
        )
    
    def test_get_enabled_channels(self):
        """Test getting list of enabled channels."""
        prefs = NotificationPreference.objects.create(
            user=self.user,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=True,
            in_app_enabled=True
        )
        
        channels = prefs.get_enabled_channels()
        
        self.assertIn('email', channels)
        self.assertIn('push', channels)
        self.assertIn('in_app', channels)
        self.assertNotIn('sms', channels)


class NotificationServiceTest(TestCase):
    """Test NotificationService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.service = NotificationService(self.user)
    
    def test_create_notification(self):
        """Test creating notification through service."""
        notifications = self.service.create_notification(
            recipient=self.user,
            title='Service Test',
            message='Test through service',
            channels=['in_app']
        )
        
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].title, 'Service Test')
    
    def test_get_unread_count(self):
        """Test getting unread count."""
        # Create some notifications
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                title=f'Notification {i}',
                message='Test',
                is_read=False
            )
        
        # Create one read notification
        Notification.objects.create(
            recipient=self.user,
            title='Read notification',
            message='Test',
            is_read=True
        )
        
        count = self.service.get_unread_count(self.user)
        self.assertEqual(count, 3)
    
    def test_mark_all_as_read(self):
        """Test marking all as read."""
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                title=f'Notification {i}',
                message='Test',
                is_read=False
            )
        
        count = self.service.mark_all_as_read(self.user)
        
        self.assertEqual(count, 3)
        self.assertEqual(
            Notification.objects.filter(recipient=self.user, is_read=False).count(),
            0
        )


class NotificationViewsTest(TestCase):
    """Test notification views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_notification_list_view(self):
        """Test notification list view."""
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_mark_as_read_view(self):
        """Test mark as read view."""
        notification = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test message'
        )
        
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': notification.id})
        )
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
    
    def test_api_view(self):
        """Test notification API view."""
        Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test message'
        )
        
        response = self.client.get(
            reverse('notifications:api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
