import jwt
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from .models import User


class ApiTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser", email="api@example.com", password="Sup3rSecret!23", role=User.Role.STUDENT
        )

    def test_valid_credentials_issue_token(self):
        response = self.client.post(
            reverse("accounts:api_token"),
            data={"username": "apiuser", "password": "Sup3rSecret!23"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        self.assertEqual(payload["username"], "apiuser")
        self.assertEqual(payload["role"], "STUDENT")

    def test_invalid_credentials_rejected(self):
        response = self.client.post(
            reverse("accounts:api_token"),
            data={"username": "apiuser", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_rejected_without_leaking_account_status(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("accounts:api_token"),
            data={"username": "apiuser", "password": "Sup3rSecret!23"},
            content_type="application/json",
        )
        # Same 401 as a wrong password - deliberately not distinguishable,
        # see the comment in views.api_token.
        self.assertEqual(response.status_code, 401)
