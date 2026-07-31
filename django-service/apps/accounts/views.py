import json

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from .decorators import admin_required, student_required
from .forms import LoginForm, RegisterForm
from .jwt_auth import issue_token_for_user
from .models import User
from apps.integrations import clients
from apps.integrations.exceptions import IntegrationError


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Account created. You can now log in.")
        return response


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("accounts:role_redirect")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


def role_redirect(request):
    """
    Single post-login landing point. Keeps LOGIN_REDIRECT_URL constant
    regardless of role, and keeps the role->URL mapping in one place
    instead of scattered across forms/views.
    """
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    if request.user.role == User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:student_dashboard")


@student_required
def student_dashboard(request):
    # Imported here rather than at module level: accounts is the app other
    # apps depend on for auth, so pulling security/notifications in at
    # import time would risk a circular import as the app registry loads.
    from apps.notifications.models import Notification
    from apps.security.models import ScanLog

    scans = ScanLog.objects.filter(user=request.user)

    try:
        score_data = clients.get_security_score(request.user)
    except IntegrationError:
        # Dashboard should never hard-fail just because the scoring
        # service is briefly unreachable - it's an enhancement on top of
        # data Django already has, not a hard dependency for the page to
        # render at all.
        score_data = None

    context = {
        "user": request.user,
        "total_scans": scans.count(),
        "malicious_count": scans.filter(status=ScanLog.Status.MALICIOUS).count(),
        "pending_count": scans.filter(status=ScanLog.Status.PENDING).count(),
        "recent_scans": scans.order_by("-created_at")[:5],
        "unread_notifications": Notification.objects.filter(recipient=request.user, is_read=False).count(),
        "security_score": score_data,
    }
    return render(request, "dashboard/student_dashboard.html", context)


@admin_required
def admin_dashboard(request):
    from apps.security.models import ScanLog, ThreatIntelEntry

    context = {
        "user": request.user,
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "total_admins": User.objects.filter(role=User.Role.ADMIN).count(),
        "total_scans": ScanLog.objects.count(),
        "malicious_count": ScanLog.objects.filter(status=ScanLog.Status.MALICIOUS).count(),
        "threat_count": ThreatIntelEntry.objects.count(),
        "recent_scans": ScanLog.objects.select_related("user").order_by("-created_at")[:8],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@admin_required
def export_users_csv(request):
    try:
        csv_text, filename = clients.fetch_export_csv(request.user, "users")
    except IntegrationError as exc:
        messages.error(request, f"Export service unavailable right now: {exc}")
        return redirect("accounts:manage_users")
    from django.http import HttpResponse
    response = HttpResponse(csv_text, content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@admin_required
def manage_users(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.all().order_by("-created_at")
    if query:
        from django.db.models import Q
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    paginator = Paginator(users, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/manage_users.html", {"page_obj": page_obj, "query": query})


@admin_required
@require_POST
def toggle_user_active(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:manage_users")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    messages.success(request, f"{target.username} is now {'active' if target.is_active else 'inactive'}.")
    return redirect("accounts:manage_users")


@admin_required
@require_POST
def change_user_role(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    new_role = request.POST.get("role")

    if new_role not in User.Role.values:
        messages.error(request, "Invalid role.")
        return redirect("accounts:manage_users")

    if target == request.user and new_role != User.Role.ADMIN:
        messages.error(request, "You cannot demote your own account.")
        return redirect("accounts:manage_users")

    target.role = new_role
    target.save(update_fields=["role"])
    messages.success(request, f"{target.username}'s role is now {target.get_role_display()}.")
    return redirect("accounts:manage_users")


@csrf_exempt
def api_token(request):
    """
    Username/password -> JWT, for stateless clients (FastAPI, Flask, any
    future SPA/mobile client) that can't carry Django's session cookie.

    csrf_exempt is correct here, not sloppy: CSRF protection defends
    cookie-based sessions from being driven by a hostile page in the
    victim's browser. This endpoint issues a bearer token from an explicit
    username+password in the request body - there's no ambient credential
    for CSRF to hijack. It's still POST-only and still goes through
    Django's normal password hashing via authenticate().
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        body = {}

    username = body.get("username") or request.POST.get("username")
    password = body.get("password") or request.POST.get("password")

    if not username or not password:
        return JsonResponse({"detail": "username and password are required."}, status=400)

    # Django's authenticate() already returns None for inactive users (via
    # ModelBackend.user_can_authenticate), so wrong-password and
    # inactive-account collapse to the same 401 here. That's intentional,
    # not an oversight: telling a caller "your account is deactivated"
    # confirms the username exists, which is exactly the kind of account-
    # enumeration signal an auth endpoint shouldn't hand out for free.
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid credentials."}, status=401)

    return JsonResponse(issue_token_for_user(user))
