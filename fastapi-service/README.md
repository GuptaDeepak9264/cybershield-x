# CyberShield X — FastAPI Service (Milestone 3)

File/URL scanning, password strength, threat intelligence lookup, security
scoring, and the AI Security Assistant. This service does **not** have its
own user table — it authenticates every request with a JWT issued by
`django-service`'s `/accounts/api/token/` endpoint, and reads/writes the
exact same MySQL tables Django's migrations own (`accounts_user`,
`security_scan_log`, `security_threat_intel`).

Every scan submitted here is real, working detection logic — SHA-256
hashing + known-hash lookup for files, heuristic pattern checks + known-
domain lookup for URLs — not a stub. It is explicitly **not** a production
antivirus/threat-intel service; see the docstrings in `app/services/` for
exactly what it does and doesn't catch.

## Requirements
- Python 3.11+
- `django-service` already migrated (this service reads its schema — see
  below) and reachable at the same MySQL database, OR both pointed at the
  same SQLite file for local dev.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# JWT_SECRET here MUST exactly match JWT_SECRET in ../django-service/.env
# DB_* here MUST point at the same database django-service uses

uvicorn app.main:app --reload --port 8001
```

Interactive API docs: `http://127.0.0.1:8001/docs`

### Getting a token to test with
This service never issues tokens itself — get one from Django:
```bash
curl -X POST http://127.0.0.1:8000/accounts/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "student1", "password": "..."}'
```
Then pass it as `Authorization: Bearer <token>` on every request here.

## Testing steps
1. `pip install -r requirements.txt` then `pytest app/tests` — 19 tests,
   all should pass. These run against an isolated in-memory SQLite DB (not
   a real MySQL connection), so they verify service *logic* — hashing,
   heuristics, RBAC, score math — independent of infrastructure.
2. **Cross-service integration proof** (this is what actually validates
   the "shared database" architecture, and is exactly what I ran before
   packaging this ZIP):
   ```bash
   # Terminal 1 - django-service, with DB_ENGINE=sqlite3 in its .env
   cd django-service && python manage.py migrate && python manage.py runserver

   # Terminal 2 - fastapi-service, SQLITE_PATH pointed at django-service/db.sqlite3
   cd fastapi-service && uvicorn app.main:app --port 8001

   # Terminal 3
   TOKEN=$(curl -s -X POST http://127.0.0.1:8000/accounts/api/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"<a student>","password":"<their password>"}' | jq -r .access_token)

   curl -X POST http://127.0.0.1:8001/api/v1/scan/url \
     -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d '{"url":"https://example.com"}'
   ```
   Then, in Django: `python manage.py shell -c "from apps.security.models import ScanLog; print(ScanLog.objects.last())"`
   — the row FastAPI just wrote should be right there, with the FK to the
   correct user intact. If it isn't, the two services aren't actually
   pointed at the same database.
3. Manual endpoint checks via `/docs`:
   - `POST /api/v1/password/check` with a common password like `password`
     → low score; with something like `Xk9#mQ2!vLp8` → high score. Confirm
     the raw password never appears anywhere in the response.
   - `POST /api/v1/scan/file` with a `.exe` vs a `.txt` → the `.exe` scores
     lower even when neither matches a known threat hash.
   - `GET /api/v1/security-score/me` before and after a scan that matches
     a threat-intel entry you added via Django's admin panel → score drops
     by exactly 20.
   - `POST /api/v1/assistant/chat` with `OPENAI_API_KEY` unset → replies
     with `"mode": "fallback"`; set a real key → `"mode": "llm"`.

## Common bugs to watch for
- **401 on every request even with a token** — almost always `JWT_SECRET`
  mismatch between the two services' `.env` files. They must be identical,
  not just "similar."
- **Module-level `settings = get_settings()` doesn't pick up test/env
  overrides** — I hit exactly this while building this milestone (see git
  history / commit message below). `get_settings()` is `lru_cache`d for
  performance, but if a module captures the *object* at import time, later
  cache-clears don't help — the module still holds the stale reference.
  Fix: call `get_settings()` fresh inside the function that needs it, not
  once at module scope, for anything that needs to be testable/overridable.
- **`sqlalchemy.exc.OperationalError: no such table`** when running
  against SQLite — you're pointing at a fresh/empty SQLite file. This
  service does not create Django's schema; run `python manage.py migrate`
  in django-service first.
- **File upload 413** — the 25 MB cap is enforced here independently of
  Django's own 25 MB cap on the upload form; if you need a different
  limit, both need to change (or the limit should move into shared config
  — noted as a future improvement).
- **AI assistant always says "fallback mode"** — `OPENAI_API_KEY` isn't
  set, or the `openai` package call raised and got silently degraded (by
  design — see `services/assistant.py`). Check `OPENAI_API_KEY` is
  actually in `.env` and non-empty.

## Interview questions this milestone maps to
- Why does FastAPI verify JWTs instead of querying `accounts_user` for
  role on every request? What's the actual cost of that tradeoff?
- Why is `ThreatIntelEntry` write access kept in Django's admin UI instead
  of also exposing a `POST /api/v1/threat-intel/` endpoint here?
- Walk through what happens, end to end, if `JWT_SECRET` differs by one
  character between the two services' `.env` files.
- Why does the AI assistant degrade to a rule-based fallback instead of
  returning a 503 when no API key is configured or the provider errors?
- Why is password-scoring logic duplicated between the client-side JS
  (Milestone 2) and this service instead of FastAPI being the only source
  of truth?

## Future improvements (deliberately deferred)
- Real malware detection (e.g., YARA rules or a third-party AV API)
  instead of hash-lookup + extension heuristics.
- A shared config/constants package between django-service and
  fastapi-service (upload size limits, allowed extensions) instead of
  each service defining its own copy.
- Rate limiting per-user on scan submission (cheap to abuse right now —
  flagged for Milestone 5 hardening).
- WebSocket or polling endpoint so the Django dashboard can show scan
  status updates without a full page refresh once Milestone 5 wires the
  two services together.

## Suggested git workflow
- Branch: `feature/milestone-3-fastapi-scanning-service`
- Commit message:
  `feat(fastapi): scanning/password/threat-intel/security-score/assistant APIs, JWT bridge from django-service`
