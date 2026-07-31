# CyberShield X — Flask Service (Milestone 4 & 6)

PDF report generation, email notifications, CSV export, analytics, and log
analysis. Like `fastapi-service`, this has no user table of its own — it
verifies JWTs issued by `django-service` and reads/writes the same MySQL
tables.

**Milestone 6 addition:** `USE_S3=True` switches PDF generation from
writing local disk (`MEDIA_ROOT`) to uploading directly to S3-compatible
object storage via `boto3`, using the same bucket and `reports/<uuid>.pdf`
key convention `django-storages` reads on the Django side. This is what
makes report generation correct once Django and Flask are separate Render
containers instead of sharing a filesystem — see `../DEPLOYMENT.md`.

## Requirements
- Python 3.11+
- `django-service` already migrated (same schema/DB story as
  `fastapi-service` — see its README for the full explanation)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# JWT_SECRET here MUST match django-service AND fastapi-service exactly
# MEDIA_ROOT should point at django-service/media so generated PDFs are
# immediately visible through Django's existing file serving

python run.py    # runs on port 8002
```

## What's real here
- **PDF reports** (`app/services/pdf_report.py`) — built with `reportlab`,
  genuinely renders a one-page summary with a real security score and a
  table of recent scans. Not a placeholder.
- **Email** (`app/services/email_service.py`) — real SMTP delivery if
  `SMTP_HOST` is set; otherwise writes to `EMAIL_OUTBOX_PATH` instead of
  failing, so the milestone is fully testable with zero mail credentials.
  Every response says which mode (`smtp` / `console`) handled it.
- **CSV export**, **analytics summary/trend**, and **log keyword/anomaly
  analysis** — all real aggregation queries against the shared scan data,
  no mocked numbers.

## A bug I hit building this, worth knowing about
Flask's `send_from_directory(directory, filename)` resolves a **relative**
`directory` against `app.root_path` (the `app/` package folder) — not the
process's working directory. I initially wrote `MEDIA_ROOT=../django-service/media`
assuming it would resolve relative to wherever `run.py` was launched from
(`flask-service/`), which worked for *writing* the PDF (plain `os.path.join`
doesn't care about Flask internals) but broke *downloading* it — the file
existed, but `send_from_directory` looked one directory too deep and 404'd.

Fixed in `app/config.py`: `MEDIA_ROOT` is now always resolved to an
absolute path at config-load time, anchored to `flask-service/` itself via
`os.path.abspath(__file__)`, so it's correct regardless of cwd or which
Flask internals happen to care about `app.root_path`. I caught this by
actually running the generate→download round trip against a live server
instead of trusting the unit tests alone (which used absolute temp
directories and never exercised the bug).

## Testing steps
1. `pytest app/tests` — 16 tests, all should pass. Covers everything from
   Milestone 4 (PDF generation, ownership checks, email console-fallback,
   CSV export scoping, analytics, log analysis) plus 3 new Milestone 6
   tests for the S3 upload path (correct bucket/key, no local file left
   behind, non-AWS endpoint URL passed through correctly).

   **Honesty note on S3 test coverage**: the S3 tests mock `boto3.client`
   rather than hitting a real bucket — this sandbox's network egress
   doesn't reach AWS or S3-compatible endpoints, so I could not verify
   against a real bucket while building this. The mocked tests confirm
   the *code* calls boto3 correctly; they don't prove a real upload/
   download round trip works. Test that yourself against a real bucket
   before trusting it in production (see `../DEPLOYMENT.md`'s
   verification checklist).
2. **Cross-service integration proof** (exactly what I ran before
   packaging this ZIP):
   ```bash
   # django-service: migrate, seed a user, get a token
   cd django-service && python manage.py migrate && python manage.py runserver
   TOKEN=$(curl -s -X POST http://127.0.0.1:8000/accounts/api/token/ \
     -H "Content-Type: application/json" -d '{"username":"...","password":"..."}' \
     | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

   # flask-service, pointed at the same db.sqlite3
   cd flask-service && python run.py

   # generate + download a real PDF
   curl -X POST http://127.0.0.1:8002/api/v1/reports/generate -H "Authorization: Bearer $TOKEN"
   curl http://127.0.0.1:8002/api/v1/reports/<id>/download -H "Authorization: Bearer $TOKEN" -o report.pdf
   file report.pdf   # should say "PDF document"
   ```
   Then in Django: `python manage.py shell -c "from apps.security.models import Report; r = Report.objects.last(); print(r.file.url, r.file.path)"`
   — `r.file.path` should point at a file that actually exists on disk,
   written by Flask, readable through Django's own `FileField`.

## Common bugs to watch for
- **The `send_from_directory` relative-path trap above** — if you ever
  move `MEDIA_ROOT` resolution logic, keep it anchored to an absolute
  path, not a relative one that "happens to work" from one launch
  directory.
- **Email "sends" but nothing arrives** — check whether `SMTP_HOST` is
  actually set; if it's blank, you're in console mode by design, check
  `EMAIL_OUTBOX_PATH` instead.
- **`reportlab` ImportError** — it's a pure-Python package with no system
  library dependencies, so this usually just means `pip install -r
  requirements.txt` wasn't run in the active environment.
- **Generated PDF has today's data but the download 404s** — same root
  cause as the bug above if you're running from a different working
  directory than expected; MEDIA_ROOT being absolute now should prevent
  this, but double check `.env` doesn't have a typo'd path.
- **Analytics/log endpoints return 403 for someone who should have
  access** — these are all `@admin_required`; only Django admins get
  system-wide analytics, matching the Django UI's own admin-only
  Analytics page from Milestone 2.

## Interview questions this milestone maps to
- Walk through exactly why `send_from_directory('../foo', file)` behaved
  differently at write-time vs. read-time in this codebase.
- Why does `send_email` return a string (`"smtp"`/`"console"`) instead of
  just returning `True`/`False` or raising on failure?
- Why is `compute_security_score` duplicated here instead of this service
  calling FastAPI's `/api/v1/security-score/me` over HTTP?
- What would need to change about `MEDIA_ROOT`/file storage before this
  architecture could survive a real multi-server deployment?
- Why does anomaly detection require a minimum baseline sample size before
  it will ever fire?

## Future improvements (deliberately deferred)
- Object storage (S3-compatible) instead of a locally-shared `media/`
  directory — required once Flask and Django aren't guaranteed to be on
  the same filesystem (Milestone 6 / Render).
- A background job queue (Celery/RQ) for PDF generation and bulk email —
  fine synchronously at this scale, would matter at real volume.
- Automatically triggering `email_notification` whenever Django creates a
  `Notification`, instead of requiring a separate admin-initiated call
  (Milestone 5 — cross-service wiring).
- A shared `security_score` calculation as one HTTP call instead of
  parallel implementations in two services, if the formula ever needs to
  get more complex than eight lines.

## Suggested git workflow
- Branch: `feature/milestone-4-flask-reports-and-utilities`
- Commit message:
  `feat(flask): PDF reports, email notifications, CSV export, analytics, log analysis`
