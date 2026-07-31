from django.contrib import admin

from .models import Report, ScanLog, ThreatIntelEntry


@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ("target", "scan_type", "status", "user", "security_score", "created_at")
    list_filter = ("scan_type", "status")
    search_fields = ("target", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ThreatIntelEntry)
class ThreatIntelEntryAdmin(admin.ModelAdmin):
    list_display = ("indicator", "indicator_type", "severity", "added_by", "created_at")
    list_filter = ("indicator_type", "severity")
    search_fields = ("indicator",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "scan_log", "created_at")
    search_fields = ("title", "user__username")
