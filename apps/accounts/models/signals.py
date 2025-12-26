"""
User-related signals for automatic profile creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .user import User, Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created."""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when user is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=User)
def manage_agent_profile(sender, instance, created, **kwargs):
    """
    Auto-create AgentProfile when user becomes agent/staff.
    This reduces admin effort by eliminating manual profile creation.
    """
    # Only for agent or staff user types
    if instance.user_type in ['agent', 'staff', 'admin']:
        # Import here to avoid circular imports
        try:
            from apps.workflow.models import AgentProfile
            # Create AgentProfile if it doesn't exist
            if not hasattr(instance, 'agent_profile'):
                AgentProfile.objects.create(user=instance)
        except ImportError:
            pass  # Workflow app might not be installed
    else:
        # Optionally deactivate agent profile if user is demoted to customer
        try:
            from apps.workflow.models import AgentProfile
            if hasattr(instance, 'agent_profile'):
                # Keep the profile but mark as unavailable
                instance.agent_profile.is_available = False
                instance.agent_profile.save(update_fields=['is_available'])
        except (ImportError, AgentProfile.DoesNotExist):
            pass
