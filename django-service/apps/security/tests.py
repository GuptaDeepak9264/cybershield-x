from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.integrations.exceptions import IntegrationError

from .models import ScanLog, ThreatIntelEntry


class ScanSubmissionTests(TestCase):
    """
    As of Milestone 5, Django no longer writes ScanLog rows itself for
    file/URL scans - it delegates to FastAPI (apps.integrations.clients),
    which writes the row on the shared DB. These tests mock that client
    function: they verify Django's view calls it correctly and handles
    both success and failure gracefully, NOT that a row appears in this
    test's isolated DB (a live FastAPI process would write that row in
    reality - the actual write path is covered by fastapi-service's own
    tests, and the full round trip is covered by the live cross-service
    integration test in this milestone's README, not by manage.py test).
    """

    def setUp(self):
        self.student = User.objects.create_user(
            username="s1", email="s1@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.client.login(username="s1", password="Sup3rSecret!23")

    @patch("apps.security.views.clients.scan_url")
    def test_url_scan_delegates_to_fastapi_and_redirects(self, mock_scan_url):
        mock_scan_url.return_value = {"status": "CLEAN", "security_score": 92}
        response = self.client.post(reverse("security:scan_url"), {"url": "https://example.com"})
        self.assertEqual(response.status_code, 302)
        mock_scan_url.assert_called_once()
        called_user, called_url = mock_scan_url.call_args[0]
        self.assertEqual(called_user, self.student)
        self.assertEqual(called_url, "https://example.com")

    @patch("apps.security.views.clients.scan_url")
    def test_url_scan_service_down_shows_error_not_crash(self, mock_scan_url):
        mock_scan_url.side_effect = IntegrationError("connection refused")
        response = self.client.post(
            reverse("security:scan_url"), {"url": "https://example.com"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertTrue(any("unavailable" in str(m) for m in messages))

    def test_file_upload_rejects_disallowed_extension_before_calling_fastapi(self):
        # Extension/size validation stays in Django's form - no reason to
        # make a network call for a request that's invalid on its face.
        bad_file = SimpleUploadedFile("virus.sh", b"echo hi", content_type="text/plain")
        with patch("apps.security.views.clients.scan_file") as mock_scan_file:
            response = self.client.post(reverse("security:upload_file"), {"file": bad_file})
            mock_scan_file.assert_not_called()
        self.assertEqual(response.status_code, 200)  # re-renders form with error

    @patch("apps.security.views.clients.scan_file")
    def test_file_upload_delegates_to_fastapi(self, mock_scan_file):
        mock_scan_file.return_value = {"status": "CLEAN", "security_score": 90}
        ok_file = SimpleUploadedFile("notes.txt", b"hello world", content_type="text/plain")
        response = self.client.post(reverse("security:upload_file"), {"file": ok_file})
        self.assertEqual(response.status_code, 302)
        mock_scan_file.assert_called_once()


class ScanHistoryIsolationTests(TestCase):
    def setUp(self):
        self.student_a = User.objects.create_user(
            username="a", email="a@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.student_b = User.objects.create_user(
            username="b", email="b@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        ScanLog.objects.create(user=self.student_a, scan_type=ScanLog.ScanType.URL, target="https://a.example.com")
        ScanLog.objects.create(user=self.student_b, scan_type=ScanLog.ScanType.URL, target="https://b.example.com")

    def test_student_only_sees_own_history(self):
        self.client.login(username="a", password="Sup3rSecret!23")
        response = self.client.get(reverse("security:history"))
        page_targets = [log.target for log in response.context["page_obj"]]
        self.assertIn("https://a.example.com", page_targets)
        self.assertNotIn("https://b.example.com", page_targets)


class ThreatIntelAdminOnlyTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="stud", email="stud@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.admin = User.objects.create_user(
            username="adm", email="adm@example.com", password="Sup3rSecret!23", role=User.Role.ADMIN
        )

    def test_student_cannot_create_threat_entry(self):
        self.client.login(username="stud", password="Sup3rSecret!23")
        response = self.client.get(reverse("security:threat_create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_threat_entry(self):
        self.client.login(username="adm", password="Sup3rSecret!23")
        response = self.client.post(reverse("security:threat_create"), {
            "indicator": "evil.example.com",
            "indicator_type": ThreatIntelEntry.IndicatorType.DOMAIN,
            "severity": ThreatIntelEntry.Severity.HIGH,
            "description": "Known phishing domain.",
        })
        self.assertEqual(response.status_code, 302)
        entry = ThreatIntelEntry.objects.get(indicator="evil.example.com")
        self.assertEqual(entry.added_by, self.admin)


class ReportGenerationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="s1", email="s1@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.client.login(username="s1", password="Sup3rSecret!23")

    @patch("apps.security.views.clients.generate_report")
    def test_generate_report_calls_flask_and_redirects(self, mock_generate):
        mock_generate.return_value = {"id": 1, "file": "reports/abc.pdf"}
        response = self.client.post(reverse("security:generate_report"))
        self.assertEqual(response.status_code, 302)
        mock_generate.assert_called_once()

    @patch("apps.security.views.clients.generate_report")
    def test_generate_report_service_down_shows_error(self, mock_generate):
        mock_generate.side_effect = IntegrationError("timeout")
        response = self.client.post(reverse("security:generate_report"), follow=True)
        messages = list(response.context["messages"])
        self.assertTrue(any("unavailable" in str(m) for m in messages))


class AssistantViewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="s1", email="s1@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )
        self.client.login(username="s1", password="Sup3rSecret!23")

    @patch("apps.security.views.clients.assistant_chat")
    def test_assistant_renders_reply_and_mode(self, mock_chat):
        mock_chat.return_value = {"reply": "Use MFA everywhere.", "mode": "fallback"}
        response = self.client.post(reverse("security:assistant"), {"message": "what is MFA?"})
        self.assertContains(response, "Use MFA everywhere.")
        self.assertContains(response, "Rule-based fallback")
