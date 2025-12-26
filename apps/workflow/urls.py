"""
URL configuration for workflow app.
"""
from django.urls import path
from apps.workflow import views

app_name = 'workflow'

urlpatterns = [
    # Agent Dashboard
    path('', views.AgentDashboardView.as_view(), name='agent_dashboard'),
    path('my-queue/', views.MyQueueView.as_view(), name='my_queue'),
    path('available/', views.AvailableTicketsView.as_view(), name='available_tickets'),
    
    # Ticket Actions
    path('ticket/<str:reference>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('ticket/<str:reference>/pick/', views.PickTicketView.as_view(), name='pick_ticket'),
    path('ticket/<str:reference>/resolve/', views.ResolveTicketView.as_view(), name='resolve_ticket'),
    path('ticket/<str:reference>/escalate/', views.EscalateTicketView.as_view(), name='escalate_ticket'),
    path('ticket/<str:reference>/note/', views.AddNoteView.as_view(), name='add_note'),
    
    # Team/Supervisor
    path('team/', views.TeamDashboardView.as_view(), name='team_dashboard'),
]
