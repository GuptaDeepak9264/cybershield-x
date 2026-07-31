# Milestone 5 — Integration

This milestone wires the pieces built in Milestones 1-4 into one working
system: **Frontend → Django → FastAPI/Flask → MySQL.**

## What actually changed

Django's browser-facing views stopped writing placeholder data and started
acting as a **gateway**: they mint a short-lived JWT for the logged-in
user (via `apps.accounts.jwt_auth.issue_token_for_user`, unchanged since
Milestone 3) and make a real server-to-server HTTP call to FastAPI or
Flask through a new `apps/integrations/clients.py` module. The downstream
service does the real work and writes to the same MySQL database Django
already reads from — so most of the time, Django's view doesn't even need
to write anything itself; it just triggers the call and redirects to a
page that was already reading from the shared DB since Milestone 2.

Concretely:

| Django page | Now calls | Effect |
|---|---|---|
| Scan a File / Scan a URL | FastAPI `POST /api/v1/scan/{file,url}` | Scan Log shows a real verdict (CLEAN/SUSPICIOUS/MALICIOUS), not stuck at PENDING |
| AI Assistant *(new page)* | FastAPI `POST /api/v1/assistant/chat` | Real chat reply, transparently labeled `llm` or `fallback` |
| Student Dashboard | FastAPI `GET /api/v1/security-score/me` | Real computed score widget (degrades gracefully if unreachable) |
| My Reports → Generate | Flask `POST /api/v1/reports/generate` | Real PDF appears, downloadable immediately (see below for why zero extra code was needed for the download itself) |
| Scan History / Admin Logs → Export CSV | Flask `GET /api/v1/export/*.csv` | Real CSV, proxied through Django so the browser session (not a JWT) is enough |
| Manage Users → Export CSV | Flask `GET /api/v1/export/users.csv` | Same proxy pattern |
| Send Notification | Flask `POST /api/v1/email/notify/{id}` | Real email delivery (or console-outbox fallback), best-effort on top of the in-app notification |
| Admin → Log Analysis *(new page)* | Flask `GET /api/v1/logs/{keyword-frequency,anomalies}` | Analysis that only exists in Flask, no Django-side duplicate |

**One thing that required zero new code**: PDF report downloads. Because
Flask writes generated PDFs into `django-service/media/reports/` (a
decision made back in Milestone 4, anticipating this), and Django's
`Report.file` FileField + `MEDIA_URL` serving were already wired up in
Milestone 2's templates, the download link in `reports.html` just started
working the moment Flask began writing real files there. That's the
payoff of setting the file-path convention correctly three milestones ago
instead of improvising it now.

## Failure handling philosophy
Every integration call is wrapped and can fail (network error, timeout,
non-2xx response) — that's `apps.integrations.exceptions.IntegrationError`.
Two different failure responses, deliberately:
- **Core operations** (scan submission, report generation, CSV export,
  the assistant): failure shows a clear "service unavailable" message and
  stops there. No fake fallback data — a scan that couldn't actually be
  scanned should not silently pretend to have a result.
- **Enhancements on top of already-successful operations** (the dashboard
  security-score widget, notification email delivery): failure degrades
  gracefully. A saved Notification is still a valid, visible in-app
  notification even if Flask couldn't be reached to also email it — the
  two are not the same operation, and one failing shouldn't undo the other.

## Running the full stack locally

Three terminals, one `.env` each (all three `JWT_SECRET` values must be
identical; all three `DB_ENGINE`/`SQLITE_PATH` — or MySQL creds — must
point at the same database):

```bash
# Terminal 1
cd django-service && cp .env.example .env  # edit as needed
python manage.py migrate
python manage.py runserver                  # :8000

# Terminal 2
cd fastapi-service && cp .env.example .env
uvicorn app.main:app --port 8001

# Terminal 3
cd flask-service && cp .env.example .env
python run.py                               # :8002
```

Visit `http://127.0.0.1:8000/`, register a student account (or use
`createsuperuser` for an admin), and every feature in the table above is
live.

## Testing steps

1. **Unit tests, all three services** (mocked cross-service calls —
   these check Django's views call the integration layer correctly and
   handle failure gracefully, without needing live FastAPI/Flask
   processes):
   ```bash
   cd django-service && python manage.py test apps      # 33 tests
   cd fastapi-service && pytest app/tests                # 19 tests
   cd flask-service && pytest app/tests                  # 13 tests
   ```
   All 65 should pass.

2. **Live full-stack smoke test** — this is the one that actually proves
   integration, and exactly what I ran before packaging this ZIP:
   - Start all three services (above).
   - Log into the Django UI as a student in a real browser (or via curl
     with a cookie jar, simulating one).
   - Submit a URL scan → **Scan History** should show a real status
     (CLEAN/SUSPICIOUS/MALICIOUS) within a second or two, not PENDING.
   - Visit **AI Assistant**, ask "how do I spot phishing?" → get a real
     reply, labeled "Rule-based fallback" (or "AI-generated" if you've set
     `OPENAI_API_KEY` in fastapi-service).
   - **My Reports** → "Generate New Report" → a PDF appears in the list
     within a second; click Download → a real, openable PDF.
   - **Scan History** → "Export CSV" → a real CSV downloads with your
     scan data.
   - As an admin, **Send Notification** (broadcast) → check
     `flask-service`'s `EMAIL_OUTBOX_PATH` (or your real inbox if SMTP is
     configured) → the message is there.
   - As an admin, **Log Analysis** → real keyword/anomaly data from Flask,
     not present anywhere in Django's own database queries.
   - Stop `fastapi-service` and try submitting a scan → should show a
     clear "Scanning service unavailable right now" message, not a 500
     error or a silently-fake result.

## Common bugs to watch for
- **Everything 401s** — `JWT_SECRET` mismatch between the three `.env`
  files. All three must be byte-for-byte identical.
- **Scans stay at PENDING forever** — that's the old Milestone 2 behavior;
  if you see it now, FastAPI probably isn't reachable at
  `FASTAPI_BASE_URL`, or Django's `.env` still has the old default without
  `FASTAPI_BASE_URL` set (check `apps/integrations/clients.py` errors in
  the Django console).
- **Report download 404s** — check `MEDIA_ROOT` in `flask-service/.env`
  is an existing, correctly-relative-or-absolute path (see
  `flask-service/README.md` for the `send_from_directory` gotcha from
  Milestone 4 — the same class of bug can resurface if `MEDIA_ROOT` is
  ever changed carelessly).
- **`ConnectionRefusedError` in Django's console when submitting a scan**
  — one of the downstream services isn't running. This should surface as
  a friendly message on the page, not a stack trace; if you see a Django
  500 instead, that's a real bug in the `IntegrationError` handling worth
  reporting.
- **Notification email delivery silently does nothing** — check
  `flask-service`'s `EMAIL_OUTBOX_PATH` file rather than assuming failure;
  console-fallback mode writes there instead of an inbox by design.

## Interview questions this milestone maps to
- Why does Django mint a fresh JWT per outgoing request instead of
  reusing the session's token across multiple integration calls in the
  same view?
- Walk through what happens end-to-end, service by service, when a
  student submits a URL scan through the browser.
- Why do scan submission failures show an error and stop, while
  notification email failures degrade gracefully instead? What's the
  actual distinction being made?
- Why does the PDF report download require zero new Django code in this
  milestone, when the CSV export required a new proxy view?
- What would break first if `fastapi-service` and `flask-service` were
  deployed to genuinely separate hosts instead of sharing a filesystem
  right now?

## Future improvements (deliberately deferred)
- Async/background processing for scan submission (currently a
  synchronous HTTP call inside the Django request-response cycle — fine
  at this scale, would need a task queue at real volume).
- Circuit breaking / retry with backoff in `apps/integrations/clients.py`
  instead of a single attempt with a flat timeout.
- Object storage for the shared `media/` directory, replacing the
  same-filesystem assumption between Django and Flask (Milestone 6).
- A shared OpenAPI/schema contract between the three services instead of
  hand-matched request/response shapes, if the API surface grows much
  further.

## Suggested git workflow
- Branch: `feature/milestone-5-full-integration`
- Commit message:
  `feat(integration): wire Django to FastAPI/Flask for scans, reports, exports, notifications, and assistant`
