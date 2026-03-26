from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import signup_view, profile_view, CustomLoginView, role_redirect_view, admin_dashboard, manager_dashboard, driver_dashboard, technician_dashboard, user_dashboard, admin_user_roles, admin_edit_user_role

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', profile_view, name='profile'),

    path('redirect/', role_redirect_view, name='role_redirect'),

    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('manager-dashboard/', manager_dashboard, name='manager_dashboard'),
    path('driver-dashboard/', driver_dashboard, name='driver_dashboard'),
    path('technician-dashboard/', technician_dashboard, name='technician_dashboard'),
    path('user-dashboard/', user_dashboard, name='user_dashboard'),
    path('admin/user-roles/', admin_user_roles, name='admin_user_roles'),
    path('admin/edit-user-role/<int:user_id>/', admin_edit_user_role, name='admin_edit_user_role'),
]