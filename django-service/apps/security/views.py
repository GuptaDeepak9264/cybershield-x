import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.accounts.decorators import admin_required, student_required
from apps.accounts.mixins import AdminRequiredMixin
from apps.integrations import clients
from apps.integrations.exceptions import IntegrationError

from .forms import FileUploadForm, ThreatIntelForm, URLScanForm
from .models import Report, ScanLog, ThreatIntelEntry

# ---------------------------------------------------------------------------
# Student-facing views
# ---------------------------------------------------------------------------


@student_required
def upload_file(request):
    if request.method == "POST":
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            # Django no longer writes the ScanLog row itself (that was the
            # Milestone 2 placeholder). It delegates to FastAPI, which
            # scans the file and writes the row to the same shared DB -
            # Django just has to redirect somewhere that reads it back.
            try:
                result = clients.scan_file(request.user, uploaded.name, uploaded.read(), uploaded.content_type)
                messages.success(
                    request,
                    f"'{uploaded.name}' scanned: {result['status']} (score {result['security_score']}).",
                )
            except IntegrationError as exc:
                messages.error(request, f"Scanning service unavailable right now: {exc}")
            return redirect("security:history")
    else:
        form = FileUploadForm()
    return render(request, "security/upload_file.html", {"form": form})


@student_required
def scan_url(request):
    if request.method == "POST":
        form = URLScanForm(request.POST)
        if form.is_valid():
            target_url = form.cleaned_data["url"]
            try:
                result = clients.scan_url(request.user, target_url)
                messages.success(
                    request,
                    f"{target_url} scanned: {result['status']} (score {result['security_score']}).",
                )
            except IntegrationError as exc:
                messages.error(request, f"Scanning service unavailable right now: {exc}")
            return redirect("security:history")
    else:
        form = URLScanForm()
    return render(request, "security/scan_url.html", {"form": form})


@student_required
def password_checker(request):
    # Scoring happens client-side (static/js/password-strength.js) for
    # instant feedback as the user types. FastAPI exposes the same rules
    # as POST /api/v1/password/check for programmatic/API callers who
    # aren't going through this form - deliberately not called from here,
    # since a network round trip on every keystroke would make the UI
    # noticeably worse for no benefit.
    return render(request, "security/password_checker.html")


@student_required
def scan_history(request):
    logs = ScanLog.objects.filter(user=request.user)
    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "security/history.html", {"page_obj": page_obj})


@student_required
def my_reports(request):
    reports = Report.objects.filter(user=request.user)
    return render(request, "security/reports.html", {"reports": reports})


@student_required
@require_POST
def generate_report(request):
    try:
        clients.generate_report(request.user)
        messages.success(request, "Report generated.")
    except IntegrationError as exc:
        messages.error(request, f"Report service unavailable right now: {exc}")
    return redirect("security:reports")


@student_required
def export_my_scans_csv(request):
    try:
        csv_text, filename = clients.fetch_export_csv(request.user, "my-scans")
    except IntegrationError as exc:
        messages.error(request, f"Export service unavailable right now: {exc}")
        return redirect("security:history")
    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@student_required
def assistant(request):
    reply = None
    mode = None
    question = ""
    if request.method == "POST":
        question = request.POST.get("message", "").strip()
        if question:
            try:
                result = clients.assistant_chat(request.user, question)
                reply, mode = result["reply"], result["mode"]
            except IntegrationError as exc:
                messages.error(request, f"Assistant service unavailable right now: {exc}")
    return render(request, "security/assistant.html", {"reply": reply, "mode": mode, "question": question})


# ---------------------------------------------------------------------------
# Admin-facing views
# ---------------------------------------------------------------------------


@admin_required
def admin_logs(request):
    logs = ScanLog.objects.select_related("user").all()

    status = request.GET.get("status")
    if status:
        logs = logs.filter(status=status)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "security/admin_logs.html",
        {"page_obj": page_obj, "status_choices": ScanLog.Status.choices, "active_status": status},
    )


@admin_required
def export_all_scans_csv(request):
    try:
        csv_text, filename = clients.fetch_export_csv(request.user, "scans")
    except IntegrationError as exc:
        messages.error(request, f"Export service unavailable right now: {exc}")
        return redirect("security:admin_logs")
    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@admin_required
def admin_reports(request):
    reports = Report.objects.select_related("user").all()
    return render(request, "security/admin_reports.html", {"reports": reports})


@admin_required
def admin_analytics(request):
    scans_by_status = ScanLog.objects.values("status").annotate(total=Count("id")).order_by("status")
    scans_by_type = ScanLog.objects.values("scan_type").annotate(total=Count("id")).order_by("scan_type")
    threats_by_severity = ThreatIntelEntry.objects.values("severity").annotate(total=Count("id")).order_by("severity")

    return render(
        request,
        "security/admin_analytics.html",
        {
            # json.dumps, not just the queryset - Python dict repr (single
            # quotes) isn't valid JSON, and Chart.js needs real JSON here.
            "scans_by_status": json.dumps(list(scans_by_status)),
            "scans_by_type": json.dumps(list(scans_by_type)),
            "threats_by_severity": json.dumps(list(threats_by_severity)),
        },
    )


@admin_required
def admin_log_analysis(request):
    """
    Pulls Flask's keyword-frequency and anomaly-detection endpoints - this
    is analysis Django itself doesn't compute; it exists only in
    flask-service, so this page is a genuine cross-service dependency, not
    a duplicate-with-fallback like security score or password scoring.
    """
    keyword_data = None
    anomaly_data = None
    error = None
    try:
        keyword_data = clients.keyword_frequency(request.user)
        anomaly_data = clients.log_anomalies(request.user)
    except IntegrationError as exc:
        error = str(exc)

    return render(
        request,
        "security/admin_log_analysis.html",
        {"keyword_data": keyword_data, "anomaly_data": anomaly_data, "error": error},
    )


class ThreatIntelListView(AdminRequiredMixin, ListView):
    model = ThreatIntelEntry
    template_name = "security/admin_threats_list.html"
    context_object_name = "threats"
    paginate_by = 20


class ThreatIntelCreateView(AdminRequiredMixin, CreateView):
    model = ThreatIntelEntry
    form_class = ThreatIntelForm
    template_name = "security/admin_threat_form.html"
    success_url = reverse_lazy("security:threat_list")

    def form_valid(self, form):
        form.instance.added_by = self.request.user
        messages.success(self.request, "Threat intel entry added.")
        return super().form_valid(form)


class ThreatIntelUpdateView(AdminRequiredMixin, UpdateView):
    model = ThreatIntelEntry
    form_class = ThreatIntelForm
    template_name = "security/admin_threat_form.html"
    success_url = reverse_lazy("security:threat_list")

    def form_valid(self, form):
        messages.success(self.request, "Threat intel entry updated.")
        return super().form_valid(form)


class ThreatIntelDeleteView(AdminRequiredMixin, DeleteView):
    model = ThreatIntelEntry
    template_name = "security/admin_threat_confirm_delete.html"
    success_url = reverse_lazy("security:threat_list")

    def form_valid(self, form):
        messages.success(self.request, "Threat intel entry removed.")
        return super().form_valid(form)
