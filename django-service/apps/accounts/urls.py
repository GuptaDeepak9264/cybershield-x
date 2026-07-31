from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("redirect/", views.role_redirect, name="role_redirect"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("users/", views.manage_users, name="manage_users"),
    path("users/export.csv", views.export_users_csv, name="export_users_csv"),
    path("users/<int:user_id>/toggle-active/", views.toggle_user_active, name="toggle_user_active"),
    path("users/<int:user_id>/change-role/", views.change_user_role, name="change_user_role"),
    path("api/token/", views.api_token, name="api_token"),
]
