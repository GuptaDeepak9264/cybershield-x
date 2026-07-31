from django.test import TestCase
from django.urls import reverse

from .models import User


class UserModelTests(TestCase):
    def test_default_role_is_student(self):
        user = User.objects.create_user(username="alice", email="alice@example.com", password="Sup3rSecret!23")
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_admin_role)

    def test_email_uniqueness_enforced_at_form_level(self):
        User.objects.create_user(username="bob", email="bob@example.com", password="Sup3rSecret!23")
        from .forms import RegisterForm

        form = RegisterForm(data={
            "username": "bob2",
            "email": "bob@example.com",
            "password1": "AnotherSecret!23",
            "password2": "AnotherSecret!23",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class RegistrationCannotEscalateRoleTests(TestCase):
    def test_role_field_cannot_be_injected_via_post(self):
        self.client.post(reverse("accounts:register"), {
            "username": "eve",
            "email": "eve@example.com",
            "password1": "Sup3rSecret!23",
            "password2": "Sup3rSecret!23",
            "role": "ADMIN",  # attempted privilege escalation
        })
        user = User.objects.get(username="eve")
        self.assertEqual(user.role, User.Role.STUDENT)


class RoleBasedAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="s1@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            username="admin1", email="a1@example.com", password="Sup3rSecret!23", role=User.Role.ADMIN
        )

    def test_student_cannot_access_admin_dashboard(self):
        self.client.login(username="student1", password="Sup3rSecret!23")
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_dashboard(self):
        self.client.login(username="admin1", password="Sup3rSecret!23")
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)


class StudentDashboardSecurityScoreTests(TestCase):
    """Milestone 5: the dashboard now shows a real FastAPI-computed score."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="s1", email="s1@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.client.login(username="s1", password="Sup3rSecret!23")

    def test_dashboard_shows_score_when_available(self):
        from unittest.mock import patch
        with patch("apps.accounts.views.clients.get_security_score") as mock_score:
            mock_score.return_value = {"score": 85, "explanation": "3 scan(s): 3 clean, 0 suspicious, 0 malicious."}
            response = self.client.get(reverse("accounts:student_dashboard"))
        self.assertContains(response, "85/100")

    def test_dashboard_degrades_gracefully_when_service_down(self):
        from unittest.mock import patch
        from apps.integrations.exceptions import IntegrationError
        with patch("apps.accounts.views.clients.get_security_score") as mock_score:
            mock_score.side_effect = IntegrationError("connection refused")
            response = self.client.get(reverse("accounts:student_dashboard"))
        # Page still renders fine, just without the score widget - a
        # briefly-down scoring service must never take the whole
        # dashboard down with it.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unavailable")


class UsersCsvExportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm", email="adm@example.com", password="Sup3rSecret!23", role=User.Role.ADMIN
        )
        self.student = User.objects.create_user(
            username="stud", email="stud@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )

    def test_student_cannot_export_users_csv(self):
        self.client.login(username="stud", password="Sup3rSecret!23")
        response = self.client.get(reverse("accounts:export_users_csv"))
        self.assertEqual(response.status_code, 403)

    def test_admin_export_proxies_flask_response(self):
        from unittest.mock import patch
        self.client.login(username="adm", password="Sup3rSecret!23")
        with patch("apps.accounts.views.clients.fetch_export_csv") as mock_fetch:
            mock_fetch.return_value = ("username,email\nstud,stud@example.com\n", "users.csv")
            response = self.client.get(reverse("accounts:export_users_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("stud@example.com", response.content.decode())
