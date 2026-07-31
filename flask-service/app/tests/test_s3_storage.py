from unittest.mock import MagicMock, patch

from app.config import Settings
from app.models import ScanLog
from app.services.pdf_report import build_security_report_pdf


def _s3_settings(media_root) -> Settings:
    return Settings(env={
        "DB_ENGINE": "sqlite3",
        "JWT_SECRET": "test-jwt-secret-different-from-secret-key-abcdef123456",
        "MEDIA_ROOT": media_root,
        "USE_S3": "True",
        "AWS_ACCESS_KEY_ID": "test-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "AWS_STORAGE_BUCKET_NAME": "cybershield-test-bucket",
        "AWS_S3_REGION_NAME": "us-east-1",
    })


class FakeScan:
    def __init__(self):
        from datetime import datetime
        self.scan_type = "URL"
        self.target = "https://example.com"
        self.status = "CLEAN"
        self.security_score = 90
        self.created_at = datetime(2026, 1, 1)


def test_s3_upload_path_calls_boto3_with_correct_bucket_and_key(media_root):
    settings = _s3_settings(media_root)

    with patch("boto3.client") as mock_boto_client:
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        relative_path = build_security_report_pdf("student1", [FakeScan()], settings)

        assert relative_path.startswith("reports/")
        assert relative_path.endswith(".pdf")
        mock_boto_client.assert_called_once_with(
            "s3", aws_access_key_id="test-key", aws_secret_access_key="test-secret", region_name="us-east-1"
        )
        mock_s3.upload_file.assert_called_once()
        args, kwargs = mock_s3.upload_file.call_args
        assert args[1] == "cybershield-test-bucket"
        assert args[2] == relative_path
        assert kwargs["ExtraArgs"]["ContentType"] == "application/pdf"


def test_s3_path_does_not_leave_local_file_behind(media_root):
    settings = _s3_settings(media_root)
    with patch("boto3.client") as mock_boto_client:
        mock_boto_client.return_value = MagicMock()
        build_security_report_pdf("student1", [], settings)

    import os
    # No reports/ dir should have been created under MEDIA_ROOT for the
    # S3 path - the temp file used for rendering gets cleaned up, and
    # nothing is ever written under media_root itself.
    assert not os.path.exists(os.path.join(media_root, "reports"))


def test_s3_endpoint_url_passed_through_for_non_aws_providers(media_root):
    settings = Settings(env={
        "DB_ENGINE": "sqlite3",
        "JWT_SECRET": "x",
        "MEDIA_ROOT": media_root,
        "USE_S3": "True",
        "AWS_ACCESS_KEY_ID": "k",
        "AWS_SECRET_ACCESS_KEY": "s",
        "AWS_STORAGE_BUCKET_NAME": "bucket",
        "AWS_S3_ENDPOINT_URL": "https://r2.example-provider.com",
    })
    with patch("boto3.client") as mock_boto_client:
        mock_boto_client.return_value = MagicMock()
        build_security_report_pdf("student1", [], settings)
        _, kwargs = mock_boto_client.call_args
        assert kwargs["endpoint_url"] == "https://r2.example-provider.com"
