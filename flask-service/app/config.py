import os
from urllib.parse import quote_plus


class Settings:
    """
    Plain-class config (not Flask's app.config dict directly) so it can be
    constructed fresh in tests with different env vars, the same lesson
    learned the hard way in fastapi-service: anything that needs to be
    overridable per-test must not be captured once at import time.
    """

    # flask-service/ - a fixed anchor for resolving relative paths from
    # .env, independent of the process's cwd (which depends on how the
    # service is launched) AND independent of Flask's app.root_path
    # (which is flask-service/app/, one level deeper - send_from_directory
    # resolves relative paths against THAT, not cwd, which is a real trap:
    # a MEDIA_ROOT that looked correct relative to cwd silently pointed one
    # directory too deep when handed to send_from_directory).
    _SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, env: dict | None = None):
        env = env if env is not None else os.environ

        self.DB_ENGINE = env.get("DB_ENGINE", "mysql")
        self.DB_NAME = env.get("DB_NAME", "cybershield_x")
        self.DB_USER = env.get("DB_USER", "cybershield_user")
        self.DB_PASSWORD = env.get("DB_PASSWORD", "change-me")
        self.DB_HOST = env.get("DB_HOST", "127.0.0.1")
        self.DB_PORT = env.get("DB_PORT", "3306")
        self.SQLITE_PATH = env.get("SQLITE_PATH", "../django-service/db.sqlite3")

        # Must match django-service's JWT_SECRET exactly, same as FastAPI.
        self.JWT_SECRET = env.get("JWT_SECRET", "change-me-to-a-different-random-string-than-SECRET_KEY")
        self.JWT_ALGORITHM = "HS256"

        # Where generated PDFs land when USE_S3=False (local disk mode).
        # Points at django-service's media/reports so Django's existing
        # Report.file / MEDIA_URL serving picks them up - see the README
        # for why this is a local-disk-sharing assumption that only holds
        # when both services are on the same filesystem.
        raw_media_root = env.get("MEDIA_ROOT", "../django-service/media")
        self.MEDIA_ROOT = (
            raw_media_root if os.path.isabs(raw_media_root)
            else os.path.normpath(os.path.join(self._SERVICE_ROOT, raw_media_root))
        )

        # Object storage (Milestone 6). When USE_S3=True, generated PDFs
        # are uploaded to the same bucket Django's django-storages backend
        # reads from, instead of written to local disk - this is what
        # makes file sharing correct once Django and Flask are separate
        # Render containers instead of sharing a filesystem.
        self.USE_S3 = env.get("USE_S3", "False") == "True"
        self.AWS_ACCESS_KEY_ID = env.get("AWS_ACCESS_KEY_ID", "")
        self.AWS_SECRET_ACCESS_KEY = env.get("AWS_SECRET_ACCESS_KEY", "")
        self.AWS_STORAGE_BUCKET_NAME = env.get("AWS_STORAGE_BUCKET_NAME", "")
        self.AWS_S3_REGION_NAME = env.get("AWS_S3_REGION_NAME", "us-east-1")
        self.AWS_S3_ENDPOINT_URL = env.get("AWS_S3_ENDPOINT_URL") or None

        # Email - SMTP if configured, console/file fallback otherwise (same
        # honest dual-mode pattern as the AI assistant in fastapi-service).
        self.SMTP_HOST = env.get("SMTP_HOST", "")
        self.SMTP_PORT = int(env.get("SMTP_PORT", "587"))
        self.SMTP_USER = env.get("SMTP_USER", "")
        self.SMTP_PASSWORD = env.get("SMTP_PASSWORD", "")
        self.SMTP_USE_TLS = env.get("SMTP_USE_TLS", "True") == "True"
        self.EMAIL_FROM = env.get("EMAIL_FROM", "no-reply@cybershieldx.local")
        # Where the console fallback writes emails it "sent" - lets a test
        # or a developer without SMTP creds inspect what would have gone out.
        self.EMAIL_OUTBOX_PATH = env.get("EMAIL_OUTBOX_PATH", "email_outbox.log")

    @property
    def database_url(self) -> str:
        if self.DB_ENGINE == "sqlite3":
            return f"sqlite:///{self.SQLITE_PATH}"
        # quote_plus escapes special characters (like the @ in your
        # password) so they can't be misread as part of the URL structure -
        # without this, a password containing @ makes pymysql think the
        # host starts at that @ instead of the real one after it.
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )