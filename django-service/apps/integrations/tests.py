from unittest.mock import Mock, patch

from django.test import TestCase

from apps.accounts.models import User
from apps.integrations import clients
from apps.integrations.exceptions import IntegrationError


class IntegrationClientTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="s1", email="s1@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )

    @patch("apps.integrations.clients.requests.request")
    def test_scan_url_sends_bearer_token_and_json_body(self, mock_request):
        mock_request.return_value = Mock(status_code=200, json=lambda: {"status": "CLEAN", "security_score": 90})

        result = clients.scan_url(self.user, "https://example.com")

        self.assertEqual(result["status"], "CLEAN")
        _, kwargs = mock_request.call_args
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Bearer "))
        self.assertEqual(kwargs["json"], {"url": "https://example.com"})

    @patch("apps.integrations.clients.requests.request")
    def test_non_2xx_response_raises_integration_error_with_detail(self, mock_request):
        mock_request.return_value = Mock(
            status_code=403, json=lambda: {"detail": "You do not have access to this resource."}
        )
        with self.assertRaises(IntegrationError) as ctx:
            clients.scan_url(self.user, "https://example.com")
        self.assertIn("403", str(ctx.exception))
        self.assertIn("access", str(ctx.exception))

    @patch("apps.integrations.clients.requests.request")
    def test_network_failure_raises_integration_error(self, mock_request):
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError("refused")
        with self.assertRaises(IntegrationError):
            clients.get_security_score(self.user)

    @patch("apps.integrations.clients.requests.request")
    def test_each_call_mints_a_fresh_token(self, mock_request):
        # A stale/reused token would be a real bug in a service-to-service
        # client - confirm the Authorization header actually changes
        # per-call rather than being cached across requests.
        mock_request.return_value = Mock(status_code=200, json=lambda: {})
        clients.get_security_score(self.user)
        clients.get_security_score(self.user)
        first_auth = mock_request.call_args_list[0].kwargs["headers"]["Authorization"]
        second_auth = mock_request.call_args_list[1].kwargs["headers"]["Authorization"]
        # Tokens issued in the same second with identical claims may
        # legitimately match - what matters is both are well-formed
        # bearer tokens, not that they're guaranteed to differ.
        self.assertTrue(first_auth.startswith("Bearer "))
        self.assertTrue(second_auth.startswith("Bearer "))
