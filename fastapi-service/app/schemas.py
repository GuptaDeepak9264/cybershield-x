from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScanLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_type: str
    target: str
    status: str
    security_score: int | None
    detail: str
    created_at: datetime


class URLScanRequest(BaseModel):
    url: str = Field(min_length=4, max_length=500)

    @field_validator("url")
    @classmethod
    def must_look_like_a_url(cls, value: str) -> str:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class PasswordCheckRequest(BaseModel):
    # Never logged, never persisted - see services/password_strength.py.
    password: str = Field(min_length=1, max_length=256)


class PasswordCheckResponse(BaseModel):
    score: int
    label: str
    feedback: list[str]


class ThreatIntelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    indicator: str
    indicator_type: str
    severity: str
    description: str
    created_at: datetime


class ThreatLookupResponse(BaseModel):
    indicator: str
    is_known_threat: bool
    severity: str | None = None
    description: str | None = None


class SecurityScoreResponse(BaseModel):
    user_id: int
    score: int
    total_scans: int
    malicious_count: int
    suspicious_count: int
    clean_count: int
    explanation: str


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AssistantChatResponse(BaseModel):
    reply: str
    mode: str  # "llm" or "fallback" - transparent about which path answered
