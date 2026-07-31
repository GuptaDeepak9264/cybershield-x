from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Config for the FastAPI scanning service.

    DB_* names deliberately match django-service/.env so the same MySQL
    credentials can be copy-pasted between the two .env files - this
    service reads and writes the exact tables Django's migrations create
    (accounts_user, security_scan_log, security_threat_intel), so the
    schema contract lives in Django, not here.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_ENGINE: str = "mysql"
    DB_NAME: str = "cybershield_x"
    DB_USER: str = "cybershield_user"
    DB_PASSWORD: str = "change-me"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: str = "3306"
    SQLITE_PATH: str = "../django-service/db.sqlite3"

    # Must match django-service's JWT_SECRET exactly - this service only
    # verifies tokens, it never issues them.
    JWT_SECRET: str = "change-me-to-a-different-random-string-than-SECRET_KEY"
    JWT_ALGORITHM: str = "HS256"

    # AI Security Assistant - optional. Without a key the assistant runs
    # in rule-based fallback mode (see services/assistant.py) rather than
    # failing outright, so the milestone is testable with zero paid deps.
    OPENAI_API_KEY: str = ""

    CORS_ALLOWED_ORIGINS: str = "http://127.0.0.1:8000,http://localhost:8000"

    @property
    def database_url(self) -> str:
        if self.DB_ENGINE == "sqlite3":
            return f"sqlite:///{self.SQLITE_PATH}"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
