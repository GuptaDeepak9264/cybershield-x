from django.urls import path

from . import views

app_name = "security"

urlpatterns = [
    # Student
    path("upload/", views.upload_file, name="upload_file"),
    path("scan-url/", views.scan_url, name="scan_url"),
    path("password-checker/", views.password_checker, name="password_checker"),
    path("history/", views.scan_history, name="history"),
    path("reports/", views.my_reports, name="reports"),
    path("reports/generate/", views.generate_report, name="generate_report"),
    path("export/my-scans.csv", views.export_my_scans_csv, name="export_my_scans_csv"),
    path("assistant/", views.assistant, name="assistant"),

    # Admin
    path("admin/logs/", views.admin_logs, name="admin_logs"),
    path("admin/logs/export.csv", views.export_all_scans_csv, name="export_all_scans_csv"),
    path("admin/reports/", views.admin_reports, name="admin_reports"),
    path("admin/analytics/", views.admin_analytics, name="admin_analytics"),
    path("admin/log-analysis/", views.admin_log_analysis, name="admin_log_analysis"),
    path("admin/threats/", views.ThreatIntelListView.as_view(), name="threat_list"),
    path("admin/threats/new/", views.ThreatIntelCreateView.as_view(), name="threat_create"),
    path("admin/threats/<int:pk>/edit/", views.ThreatIntelUpdateView.as_view(), name="threat_update"),
    path("admin/threats/<int:pk>/delete/", views.ThreatIntelDeleteView.as_view(), name="threat_delete"),
]
