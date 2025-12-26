"""
Search URL configuration.
"""
from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    # Main search page
    path('', views.GlobalSearchView.as_view(), name='global'),
    
    # API endpoints
    path('api/', views.SearchAPIView.as_view(), name='api'),
    path('suggestions/', views.SuggestionsView.as_view(), name='suggestions'),
    path('recent/', views.RecentSearchesView.as_view(), name='recent'),
    path('click/', views.SearchRecordClickView.as_view(), name='record_click'),
    
    # Modal content
    path('modal/', views.SearchModalView.as_view(), name='modal'),
    
    # Admin
    path('rebuild/', views.RebuildIndexView.as_view(), name='rebuild_index'),
]
