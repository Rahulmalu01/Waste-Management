from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from .forms import CustomSignupForm, CustomUserUpdateForm, RoleUpdateForm
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .models import CustomUser

def redirect_user_by_role(user):
    if user.role == 'ADMIN':
        return 'admin_dashboard'
    elif user.role == 'MANAGER':
        return 'manager_dashboard'
    elif user.role == 'DRIVER':
        return 'driver_dashboard'
    elif user.role == 'TECHNICIAN':
        return 'technician_dashboard'
    else:
        return 'user_dashboard'

class CustomLoginView(LoginView):
    template_name = 'login.html'
    def get_success_url(self):
        return reverse_lazy('role_redirect')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_user_by_role(request.user))
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'GENERAL'
            user.save()
            login(request, user)
            return redirect('profile')
    else:
        form = CustomSignupForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = CustomUserUpdateForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})

@login_required
def role_redirect_view(request):
    return redirect(redirect_user_by_role(request.user))

@login_required
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        return redirect('role_redirect')
    return render(request, 'accounts/admin_dashboard.html')

@login_required
def admin_user_roles(request):
    if request.user.role != 'ADMIN':
        return redirect('role_redirect')
    users = CustomUser.objects.all()
    return render(request, 'accounts/admin_user_roles.html', {'users': users})

@login_required
def admin_edit_user_role(request, user_id):
    if request.user.role != 'ADMIN':
        return redirect('role_redirect')
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = RoleUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_user_roles')
    else:
        form = RoleUpdateForm(instance=user)
    return render(request, 'accounts/admin_edit_user_role.html', {'form': form, 'user': user})

@login_required
def manager_dashboard(request):
    if request.user.role != 'MANAGER':
        return redirect('role_redirect')
    return render(request, 'accounts/manager_dashboard.html')

@login_required
def driver_dashboard(request):
    if request.user.role != 'DRIVER':
        return redirect('role_redirect')
    return render(request, 'accounts/driver_dashboard.html')

@login_required
def technician_dashboard(request):
    if request.user.role != 'TECHNICIAN':
        return redirect('role_redirect')
    return render(request, 'accounts/technician_dashboard.html')

@login_required
def user_dashboard(request):
    if request.user.role != 'GENERAL':
        return redirect('role_redirect')
    return render(request, 'accounts/user_dashboard.html')
