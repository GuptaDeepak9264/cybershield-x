from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import assistant, password, scans, security_score, threat_intel

settings = get_settings()

app = FastAPI(
    title="CyberShield X - Scanning API",
    description=(
        "File/URL scanning, password strength, threat intelligence lookup, "
        "security scoring, and the AI security assistant. Authenticated "
        "with JWTs issued by the Django service's /accounts/api/token/ "
        "endpoint."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scans.router)
app.include_router(password.router)
app.include_router(threat_intel.router)
app.include_router(security_score.router)
app.include_router(assistant.router)


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok", "service": "cybershield-x-fastapi"}
