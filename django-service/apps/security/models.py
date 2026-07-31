from django.conf import settings
from django.db import models


def scan_upload_path(instance, filename):
    return f"scans/user_{instance.user_id}/{filename}"


class ScanLog(models.Model):
    """
    One row per scan request (file or URL).

    Django owns creation of this record and its lifecycle status - it's
    the audit trail / "security log" the brief calls for. The actual
    scanning work (hashing, signature lookups, verdicts) is FastAPI's job
    starting Milestone 3; until that's wired up in Milestone 5, every scan
    created here simply sits at PENDING. That's intentional, not a bug:
    this milestone proves the logging/history/UI path end to end so the
    engine can be dropped in later without touching this model's contract.
    """

    class ScanType(models.TextChoices):
        FILE = "FILE", "File"
        URL = "URL", "URL"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CLEAN = "CLEAN", "Clean"
        SUSPICIOUS = "SUSPICIOUS", "Suspicious"
        MALICIOUS = "MALICIOUS", "Malicious"
        ERROR = "ERROR", "Error"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scan_logs")
    scan_type = models.CharField(max_length=10, choices=ScanType.choices)
    target = models.CharField(max_length=500, help_text="Original filename or scanned URL.")
    file = models.FileField(upload_to=scan_upload_path, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    security_score = models.PositiveSmallIntegerField(null=True, blank=True, help_text="0-100, higher is safer.")
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "security_scan_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"[{self.scan_type}] {self.target} ({self.status})"


class ThreatIntelEntry(models.Model):
    """
    Admin-curated threat intelligence: known-bad indicators the scanning
    engine (Milestone 3) will check submissions against. Django owns CRUD
    here because it's low-volume, human-curated data - not a fit for a
    high-throughput API service.
    """

    class IndicatorType(models.TextChoices):
        FILE_HASH = "FILE_HASH", "File Hash (SHA-256)"
        DOMAIN = "DOMAIN", "Domain"
        URL = "URL", "URL"
        IP = "IP", "IP Address"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    indicator = models.CharField(max_length=500, unique=True)
    indicator_type = models.CharField(max_length=10, choices=IndicatorType.choices)
    severity = models.CharField(max_length=8, choices=Severity.choices, default=Severity.MEDIUM)
    description = models.TextField(blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="threat_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "security_threat_intel"
        ordering = ["-created_at"]
        verbose_name_plural = "Threat intel entries"

    def __str__(self):
        return f"{self.indicator} ({self.severity})"


class Report(models.Model):
    """
    Metadata row for a generated report. The PDF itself is produced by
    Flask's report service (Milestone 4) and will populate `file` once
    that pipeline is connected in Milestone 5 - this table exists now so
    the "My Reports" UI has something real to list against.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    scan_log = models.ForeignKey(ScanLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="reports/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "security_report"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
