from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.integrations.exceptions import IntegrationError

from .models import Notification


class NotificationVisibilityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm", email="adm@example.com", password="Sup3rSecret!23", role=User.Role.ADMIN
        )
        self.student_a = User.objects.create_user(
            username="a", email="a@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.student_b = User.objects.create_user(
            username="b", email="b@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )

    def test_broadcast_visible_to_all_students(self):
        Notification.objects.create(sender=self.admin, recipient=None, title="Maintenance", message="Downtime tonight.")
        self.client.login(username="a", password="Sup3rSecret!23")
        response = self.client.get(reverse("notifications:inbox"))
        self.assertContains(response, "Maintenance")

    def test_targeted_notification_not_visible_to_other_student(self):
        Notification.objects.create(sender=self.admin, recipient=self.student_a, title="Just for A", message="Hi A.")
        self.client.login(username="b", password="Sup3rSecret!23")
        response = self.client.get(reverse("notifications:inbox"))
        self.assertNotContains(response, "Just for A")

    def test_student_cannot_send_notifications(self):
        self.client.login(username="a", password="Sup3rSecret!23")
        response = self.client.get(reverse("notifications:send"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_broadcast(self):
        self.client.login(username="adm", password="Sup3rSecret!23")
        response = self.client.post(reverse("notifications:send"), {
            "recipient": "",
            "title": "System update",
            "message": "New scanning rules deployed.",
        })
        self.assertEqual(response.status_code, 302)
        note = Notification.objects.get(title="System update")
        self.assertTrue(note.is_broadcast)


class NotificationEmailDeliveryTests(TestCase):
    """
    Milestone 5: sending a notification now also attempts real email
    delivery via Flask. These tests mock that call - the live cross-
    service proof (Flask actually sending/logging the email) is in
    flask-service's own tests and this milestone's integration test.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm", email="adm@example.com", password="Sup3rSecret!23", role=User.Role.ADMIN
        )
        self.client.login(username="adm", password="Sup3rSecret!23")

    @patch("apps.notifications.views.clients.notify_email")
    def test_send_notification_triggers_email_delivery(self, mock_notify):
        mock_notify.return_value = {"count": 3, "delivered_to": []}
        response = self.client.post(reverse("notifications:send"), {
            "recipient": "", "title": "Hello", "message": "World.",
        }, follow=True)
        mock_notify.assert_called_once()
        messages = list(response.context["messages"])
        self.assertTrue(any("emailed to 3 recipient" in str(m) for m in messages))

    @patch("apps.notifications.views.clients.notify_email")
    def test_notification_still_saved_even_if_email_delivery_fails(self, mock_notify):
        # The in-app notification must not be lost just because Flask is
        # briefly unreachable - it's a best-effort enhancement, not a
        # precondition for the notification existing at all.
        mock_notify.side_effect = IntegrationError("connection refused")
        response = self.client.post(reverse("notifications:send"), {
            "recipient": "", "title": "Hello", "message": "World.",
        }, follow=True)
        self.assertTrue(Notification.objects.filter(title="Hello").exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("email delivery failed" in str(m) for m in messages))
