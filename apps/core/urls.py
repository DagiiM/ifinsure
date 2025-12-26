"""
Core URL configuration.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # User Reviews
    path('review/', views.SubmitReviewView.as_view(), name='submit_review'),
    path('review/thanks/', views.ReviewThanksView.as_view(), name='review_thanks'),
    path('my-reviews/', views.MyReviewsView.as_view(), name='my_reviews'),
    
    # Sitemap
    path('sitemap/', views.SitemapView.as_view(), name='sitemap'),
]
