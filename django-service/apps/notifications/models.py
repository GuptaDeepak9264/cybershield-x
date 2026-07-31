from django.conf import settings
from django.db import models


class NotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        """Everything a given user should see: broadcasts + anything sent directly to them."""
        return self.filter(models.Q(recipient=user) | models.Q(recipient__isnull=True))


class Notification(models.Model):
    """
    Admin -> student(s) messaging.

    `recipient=None` means broadcast-to-everyone. Read-state tracking is
    only meaningful for targeted notifications here (`is_read` on a
    broadcast row would mean "read by *someone*", which isn't useful) -
    per-recipient read receipts on broadcasts is a reasonable follow-up
    (a through-table of User<->Notification) but isn't needed for the
    Milestone 2 UI, so it's deferred rather than built speculatively.
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_notifications"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="Leave blank to broadcast to every user.",
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False, help_text="Only meaningful for targeted notifications.")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]

    def __str__(self):
        target = self.recipient.username if self.recipient else "everyone"
        return f"{self.title} -> {target}"

    @property
    def is_broadcast(self) -> bool:
        return self.recipient_id is None
