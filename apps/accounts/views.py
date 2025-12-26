from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect

from apps.core.views.base import (
    BaseView, BaseTemplateView, BaseCreateView, BaseUpdateView,
    MessageMixin, LoginRequiredMixin, BaseContextMixin
)
from django.views.generic import CreateView
from .forms import (
    LoginForm,
    RegistrationForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)
from .services import AccountService


class CustomLoginView(BaseContextMixin, LoginView):
    """Custom login view with styled form."""
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    page_title = 'Login'
    
    def get_success_url(self):
        return reverse_lazy('dashboard:home')
    
    def form_valid(self, form):
        # Handle remember me
        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)
        
        response = super().form_valid(form)
        
        # Log the login via service
        account_service = self.get_service(AccountService)
        account_service.log_login(self.request.user)
        
        messages.success(self.request, f'Welcome back, {self.request.user.get_short_name()}!')
        return response


class CustomLogoutView(BaseContextMixin, LogoutView):
    """Custom logout view."""
    next_page = 'dashboard:home'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Log the logout via service
            account_service = self.get_service(AccountService)
            account_service.log_logout(request.user)
            messages.info(request, 'You have been logged out.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_page_title(self):
        return 'Logout'


class RegisterView(BaseContextMixin, MessageMixin, CreateView):
    """
    User registration view.
    Uses AccountService for user creation with audit logging.
    """
    template_name = 'accounts/register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('accounts:login')
    success_message = 'Account created successfully! Please log in.'
    page_title = 'Create Account'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log registration via service
        account_service = AccountService(user=self.object)
        account_service._log_action('create', instance=self.object, details={'event': 'User registration'})
        
        return response


class ProfileView(BaseTemplateView):
    """View user profile."""
    template_name = 'accounts/profile.html'
    page_title = 'My Profile'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['profile'] = self.request.user.profile
        return context


class ProfileUpdateView(BaseUpdateView):
    """
    Update user profile.
    Uses AccountService for profile updates with audit logging.
    """
    template_name = 'accounts/profile_edit.html'
    form_class = UserUpdateForm
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Profile updated successfully.'
    page_title = 'Edit Profile'
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['profile_form'] = ProfileUpdateForm(
                self.request.POST,
                self.request.FILES,
                instance=self.request.user.profile
            )
        else:
            context['profile_form'] = ProfileUpdateForm(
                instance=self.request.user.profile
            )
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        
        account_service = self.get_service(AccountService)
        
        # Collect user field updates
        user_updates = {field: form.cleaned_data.get(field) for field in form.changed_data}
        
        # Update user via service
        if user_updates:
            account_service.update_user(user=self.request.user, **user_updates)
        
        # Collect profile field updates
        if profile_form.is_valid():
            profile_updates = {field: profile_form.cleaned_data.get(field) for field in profile_form.changed_data}
            
            # Update profile via service
            if profile_updates:
                account_service.update_profile(user=self.request.user, **profile_updates)
            else:
                # Save anyway if form is valid (handles file uploads etc)
                profile_form.save()
        
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class CustomPasswordChangeView(BaseContextMixin, PasswordChangeView, MessageMixin):
    """
    Custom password change view.
    Uses AccountService for audit logging.
    """
    template_name = 'accounts/password_change.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Password changed successfully.'
    page_title = 'Change Password'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log password change via service
        account_service = self.get_service(AccountService)
        account_service.change_password(self.request.user, form.cleaned_data.get('new_password1'))
        
        return response
