"""
Management command to set up initial workclasses and departments.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.workflow.models import Department, WorkClass, AgentProfile
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up initial departments and workclasses'
    
    def handle(self, *args, **options):
        # Create departments
        departments = [
            {'code': 'CLAIMS', 'name': 'Claims Department', 'description': 'Handles all insurance claims'},
            {'code': 'POLICIES', 'name': 'Policy Department', 'description': 'Policy issuance and management'},
            {'code': 'BILLING', 'name': 'Billing Department', 'description': 'Payments and billing'},
            {'code': 'SUPPORT', 'name': 'Customer Support', 'description': 'Customer inquiries and support'},
            {'code': 'SALES', 'name': 'Sales Department', 'description': 'New business and renewals'},
        ]
        
        created_depts = 0
        for dept_data in departments:
            dept, created = Department.objects.update_or_create(
                code=dept_data['code'],
                defaults=dept_data
            )
            if created:
                created_depts += 1
                self.stdout.write(self.style.SUCCESS(f'Created department: {dept.name}'))
        
        # Create workclasses
        workclasses = [
            # Level 1 - Trainee
            {
                'code': 'TRAINEE',
                'name': 'Trainee',
                'level': 1,
                'description': 'Learning mode - view only access',
                'monetary_limit': Decimal('0.00'),
                'daily_ticket_limit': 5,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': False,
                    'can_resolve_tickets': False,
                }
            },
            # Level 2 - Junior Agent (Claims)
            {
                'code': 'CLAIMS_JUNIOR',
                'name': 'Junior Claims Agent',
                'level': 2,
                'department': 'CLAIMS',
                'description': 'Claims intake and documentation',
                'monetary_limit': Decimal('0.00'),
                'daily_ticket_limit': 15,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': False,
                    'can_create_claims': True,
                }
            },
            # Level 2 - Junior Agent (Policies)
            {
                'code': 'POLICIES_JUNIOR',
                'name': 'Junior Policy Agent',
                'level': 2,
                'department': 'POLICIES',
                'description': 'Policy applications and data entry',
                'monetary_limit': Decimal('50000.00'),
                'daily_ticket_limit': 15,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': False,
                    'can_issue_policies': False,
                }
            },
            # Level 3 - Agent (Claims)
            {
                'code': 'CLAIMS_AGENT',
                'name': 'Claims Agent',
                'level': 3,
                'department': 'CLAIMS',
                'description': 'Process and approve standard claims',
                'monetary_limit': Decimal('100000.00'),
                'daily_ticket_limit': 20,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': True,
                    'can_create_claims': True,
                    'can_approve_claims': True,
                    'can_reject_claims': True,
                }
            },
            # Level 3 - Agent (Policies)
            {
                'code': 'POLICIES_AGENT',
                'name': 'Policy Agent',
                'level': 3,
                'department': 'POLICIES',
                'description': 'Issue and manage policies',
                'monetary_limit': Decimal('500000.00'),
                'daily_ticket_limit': 20,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': True,
                    'can_issue_policies': True,
                    'can_cancel_policies': False,
                }
            },
            # Level 4 - Senior Agent (Claims)
            {
                'code': 'CLAIMS_SENIOR',
                'name': 'Senior Claims Agent',
                'level': 4,
                'department': 'CLAIMS',
                'description': 'Handle complex claims, escalation point',
                'monetary_limit': Decimal('500000.00'),
                'daily_ticket_limit': 15,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': True,
                    'can_create_claims': True,
                    'can_approve_claims': True,
                    'can_reject_claims': True,
                    'can_assign_tickets': True,
                    'can_view_team': True,
                }
            },
            # Level 4 - Senior Agent (Policies)
            {
                'code': 'POLICIES_SENIOR',
                'name': 'Senior Policy Agent',
                'level': 4,
                'department': 'POLICIES',
                'description': 'Handle complex policies, team lead',
                'monetary_limit': Decimal('2000000.00'),
                'daily_ticket_limit': 15,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': True,
                    'can_issue_policies': True,
                    'can_cancel_policies': True,
                    'can_assign_tickets': True,
                    'can_view_team': True,
                }
            },
            # Level 5 - Supervisor
            {
                'code': 'SUPERVISOR',
                'name': 'Supervisor',
                'level': 5,
                'description': 'Full access, team management',
                'monetary_limit': Decimal('10000000.00'),
                'daily_ticket_limit': 10,
                'permissions': {
                    'can_view_tickets': True,
                    'can_add_notes': True,
                    'can_pick_tickets': True,
                    'can_resolve_tickets': True,
                    'can_create_claims': True,
                    'can_approve_claims': True,
                    'can_reject_claims': True,
                    'can_issue_policies': True,
                    'can_cancel_policies': True,
                    'can_assign_tickets': True,
                    'can_view_team': True,
                    'can_view_reports': True,
                    'can_manage_agents': True,
                }
            },
            # Level 5 - Admin
            {
                'code': 'ADMIN',
                'name': 'Administrator',
                'level': 5,
                'description': 'System administrator with full access',
                'monetary_limit': Decimal('999999999.00'),
                'daily_ticket_limit': 100,
                'permissions': {
                    'all': True,
                }
            },
        ]
        
        created_wc = 0
        for wc_data in workclasses:
            dept_code = wc_data.pop('department', None)
            if dept_code:
                wc_data['department'] = Department.objects.get(code=dept_code)
            
            wc, created = WorkClass.objects.update_or_create(
                code=wc_data['code'],
                defaults=wc_data
            )
            if created:
                created_wc += 1
                self.stdout.write(self.style.SUCCESS(f'Created workclass: {wc.name} (L{wc.level})'))
            else:
                self.stdout.write(f'Updated workclass: {wc.name}')
        
        # Create agent profiles for existing staff users
        staff_users = User.objects.filter(is_staff=True)
        created_profiles = 0
        for user in staff_users:
            profile, created = AgentProfile.objects.get_or_create(user=user)
            if created:
                created_profiles += 1
                # Assign supervisor workclass to staff
                supervisor_wc = WorkClass.objects.get(code='SUPERVISOR')
                profile.workclasses.add(supervisor_wc)
                profile.primary_workclass = supervisor_wc
                profile.save()
                self.stdout.write(self.style.SUCCESS(f'Created agent profile: {user.email}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSummary:\n'
            f'  Departments: {created_depts} created\n'
            f'  WorkClasses: {created_wc} created\n'
            f'  Agent Profiles: {created_profiles} created'
        ))
