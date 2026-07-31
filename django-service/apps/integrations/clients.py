import requests
from django.conf import settings

from apps.accounts.jwt_auth import issue_token_for_user

from .exceptions import IntegrationError


def _bearer_headers(user) -> dict:
    token = issue_token_for_user(user)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _handle_response(response: requests.Response):
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise IntegrationError(f"Service returned {response.status_code}: {detail}", status_code=response.status_code)
    return response


def _request(method: str, url: str, user, **kwargs):
    try:
        response = requests.request(
            method, url, headers=_bearer_headers(user), timeout=settings.INTEGRATION_TIMEOUT_SECONDS, **kwargs
        )
    except requests.exceptions.RequestException as exc:
        raise IntegrationError(f"Could not reach {url}: {exc}") from exc
    return _handle_response(response)


# --- FastAPI: scanning, password, threat intel, security score, assistant ---

def scan_file(user, filename: str, content: bytes, content_type: str) -> dict:
    url = f"{settings.FASTAPI_BASE_URL}/api/v1/scan/file"
    files = {"file": (filename, content, content_type or "application/octet-stream")}
    return _request("POST", url, user, files=files).json()


def scan_url(user, target_url: str) -> dict:
    url = f"{settings.FASTAPI_BASE_URL}/api/v1/scan/url"
    return _request("POST", url, user, json={"url": target_url}).json()


def get_security_score(user) -> dict:
    url = f"{settings.FASTAPI_BASE_URL}/api/v1/security-score/me"
    return _request("GET", url, user).json()


def assistant_chat(user, message: str) -> dict:
    url = f"{settings.FASTAPI_BASE_URL}/api/v1/assistant/chat"
    return _request("POST", url, user, json={"message": message}).json()


# --- Flask: reports, email, export, analytics, log analysis ---

def generate_report(user) -> dict:
    url = f"{settings.FLASK_BASE_URL}/api/v1/reports/generate"
    return _request("POST", url, user).json()


def fetch_export_csv(user, export_path: str) -> tuple[str, str]:
    """Returns (csv_text, filename). export_path is e.g. 'my-scans', 'scans', 'users'."""
    url = f"{settings.FLASK_BASE_URL}/api/v1/export/{export_path}.csv"
    response = _request("GET", url, user)
    return response.text, f"{export_path}.csv"


def notify_email(admin_user, notification_id: int) -> dict:
    url = f"{settings.FLASK_BASE_URL}/api/v1/email/notify/{notification_id}"
    return _request("POST", url, admin_user).json()


def keyword_frequency(admin_user) -> dict:
    url = f"{settings.FLASK_BASE_URL}/api/v1/logs/keyword-frequency"
    return _request("GET", url, admin_user).json()


def log_anomalies(admin_user) -> dict:
    url = f"{settings.FLASK_BASE_URL}/api/v1/logs/anomalies"
    return _request("GET", url, admin_user).json()
