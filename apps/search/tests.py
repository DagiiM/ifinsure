"""
Search tests.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.search.models import SearchIndex, SearchHistory
from apps.search.services import SearchService

User = get_user_model()


class SearchIndexModelTest(TestCase):
    """Test SearchIndex model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_index_entry(self):
        """Test creating a search index entry."""
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(User)
        
        entry = SearchIndex.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            title='Test User',
            subtitle='test@example.com',
            model_name='user',
            model_verbose_name='User',
            visibility='private',
            owner_id=self.user.pk
        )
        
        self.assertEqual(entry.title, 'Test User')
        self.assertEqual(entry.model_name, 'user')
    
    def test_to_dict(self):
        """Test serialization."""
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(User)
        
        entry = SearchIndex.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            title='Test User',
            model_name='user'
        )
        
        data = entry.to_dict()
        
        self.assertEqual(data['title'], 'Test User')
        self.assertEqual(data['model'], 'user')


class SearchHistoryModelTest(TestCase):
    """Test SearchHistory model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_history(self):
        """Test creating search history."""
        history = SearchHistory.objects.create(
            user=self.user,
            query='test query',
            results_count=10
        )
        
        self.assertEqual(history.query, 'test query')
        self.assertEqual(history.results_count, 10)
    
    def test_recent_for_user(self):
        """Test getting recent searches."""
        for i in range(5):
            SearchHistory.objects.create(
                user=self.user,
                query=f'query {i}',
                results_count=i
            )
        
        recent = SearchHistory.objects.recent_for_user(self.user, limit=3)
        
        self.assertEqual(len(recent), 3)


class SearchServiceTest(TestCase):
    """Test SearchService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.service = SearchService(self.user)
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        results = self.service.search('')
        
        self.assertEqual(results['total'], 0)
        self.assertEqual(results['all'], [])
    
    def test_search_short_query(self):
        """Test search with too short query."""
        results = self.service.search('a')
        
        self.assertEqual(results['total'], 0)
    
    def test_get_registered_models(self):
        """Test getting registered models."""
        models = SearchService.get_registered_models()
        
        # Should return a list
        self.assertIsInstance(models, list)
    
    def test_recent_searches(self):
        """Test getting recent searches."""
        SearchHistory.objects.create(
            user=self.user,
            query='test search',
            results_count=5
        )
        
        recent = self.service.recent_searches()
        
        self.assertIsInstance(recent, list)


class SearchViewsTest(TestCase):
    """Test search views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_global_search_view(self):
        """Test global search page."""
        response = self.client.get(reverse('search:global'))
        self.assertEqual(response.status_code, 200)
    
    def test_global_search_with_query(self):
        """Test search with query parameter."""
        response = self.client.get(reverse('search:global'), {'q': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.context)
    
    def test_search_api_view(self):
        """Test search API endpoint."""
        response = self.client.get(
            reverse('search:api'),
            {'q': 'test'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_suggestions_view(self):
        """Test suggestions API."""
        response = self.client.get(
            reverse('search:suggestions'),
            {'q': 'test'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
