from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, student_required
from apps.integrations import clients
from apps.integrations.exceptions import IntegrationError

from .forms import NotificationForm
from .models import Notification


@admin_required
def send_notification(request):
    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.sender = request.user
            notification.save()
            target = notification.recipient.username if notification.recipient else "all students"

            # Delivering the email is a real cross-service call to Flask,
            # not guaranteed to succeed - but a failed email delivery
            # should never undo the notification itself (the student
            # still sees it in their in-app inbox either way). So the
            # Notification row is saved first, unconditionally, and email
            # delivery is best-effort on top of that.
            try:
                result = clients.notify_email(request.user, notification.id)
                messages.success(
                    request, f"Notification sent to {target} and emailed to {result['count']} recipient(s)."
                )
            except IntegrationError as exc:
                messages.warning(
                    request,
                    f"Notification sent to {target} in-app, but email delivery failed: {exc}",
                )
            return redirect("notifications:sent_list")
    else:
        form = NotificationForm()
    return render(request, "notifications/send.html", {"form": form})


@admin_required
def sent_list(request):
    notifications = Notification.objects.select_related("recipient", "sender")
    return render(request, "notifications/sent_list.html", {"notifications": notifications})


@student_required
def inbox(request):
    notifications = Notification.objects.for_user(request.user)
    return render(request, "notifications/inbox.html", {"notifications": notifications})


@student_required
@require_POST
def mark_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect("notifications:inbox")
