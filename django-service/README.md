# CyberShield X — Django Service (Milestones 1, 2, 5 & 6)

**Note:** this is one service in a multi-service monorepo — see the
top-level `../README.md`, `../MILESTONE_5_INTEGRATION.md`, and
`../DEPLOYMENT.md` for how it relates to `fastapi-service/` and
`flask-service/`, and how to deploy it.

**Milestone 1 scope:** Django project skeleton, MySQL wiring, custom user
model, role-based authentication (Student / Admin).

**Milestone 2 scope:** Frontend dashboard shell (dark Bootstrap 5,
role-based sidebar), Student Panel (file/URL scan submission, password
strength checker, scan history, reports list, notification inbox), Admin
Panel (user management, threat intelligence CRUD, scan log viewer,
analytics with Chart.js, report list, notification composer).

**Milestone 3 addition:** a JWT bridge (`POST /accounts/api/token/`) so
`fastapi-service` can authenticate requests without sharing Django's
session cookie.

**Milestone 5 addition:** `apps/integrations/` — Django now acts as a
gateway to FastAPI and Flask. Scan submission, report generation, CSV
export, notification email delivery, and a new AI Assistant page and
admin Log Analysis page all make real server-to-server calls to the other
two services. See `../MILESTONE_5_INTEGRATION.md` for the full picture.

Scans submitted through the UI now show a real verdict (not stuck at
`PENDING`) as long as `fastapi-service` is reachable.

**Milestone 6 addition:** production deployment support — WhiteNoise for
self-serving static files (see `DEPLOYMENT.md` for why there's no
separate frontend host), `django-storages` + `boto3` for S3-compatible
object storage (`USE_S3=True`), `gunicorn` as the production WSGI server,
and DEBUG-derived production security hardening (HSTS, SSL redirect).
Local dev is unaffected — `USE_S3=False` (the default) keeps using local
disk exactly as in Milestones 1-5.

## Requirements
- Python 3.11+
- MySQL 8.x server (or use the SQLite fallback below for a quick local check)

## Setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set SECRET_KEY, and either MySQL creds or DB_ENGINE=sqlite3

python manage.py migrate
python manage.py createsuperuser  # creates an admin via Django's own flow
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

### MySQL setup (if not already provisioned)
```sql
CREATE DATABASE cybershield_x CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cybershield_user'@'%' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON cybershield_x.* TO 'cybershield_user'@'%';
FLUSH PRIVILEGES;
```
Then set `DB_ENGINE=mysql` and the matching `DB_*` values in `.env`.

## Testing steps
1. `python manage.py check` — should report no issues.
2. `python manage.py migrate` — should apply cleanly on a fresh DB.
3. `python manage.py test apps` — 33 tests across `accounts`, `security`,
   `notifications`, and `integrations`, all should pass (unaffected by
   Milestone 6's deployment changes — `USE_S3` defaults `False` in tests,
   same local-disk behavior as before). As of Milestone 5, the
   scan-submission and report-generation tests mock
   `apps.integrations.clients` rather than asserting direct DB writes
   (Django no longer writes those rows itself) — see the docstring at the
   top of `apps/security/tests.py` for why, and
   `../MILESTONE_5_INTEGRATION.md` for the live cross-service test that
   proves the real round trip.
4. **Production path check** (what I ran before packaging this ZIP):
   `DEBUG=False`, `python manage.py collectstatic --noinput`, then serve
   with `gunicorn config.wsgi:application` instead of `runserver` —
   confirms WhiteNoise's manifest-hashed static files actually resolve
   under the production storage backend, not just the dev one.
4. Manual smoke test (this is exactly what I ran before packaging this ZIP):
   - Log in as a student → dashboard shows real stat cards (0s on a fresh
     DB) and quick links to Scan a File / Scan a URL / Check a Password.
   - Submit a URL at **Scan a URL** → redirects to **Scan History**, entry
     appears with status `Pending`.
   - Open **Password Checker**, type a password → strength bar and
     feedback update live, entirely client-side (open dev tools / network
     tab to confirm nothing is sent anywhere).
   - Log in as an admin → **Manage Users** lets you search,
     activate/deactivate, and promote/demote (self-demotion and
     self-deactivation are blocked with a message).
   - **Threat Database** → add an indicator, confirm it appears in the
     list, edit it, delete it (confirmation page first).
   - **Analytics** → three Chart.js charts render from real aggregate
     queries (bar/doughnut/horizontal bar).
   - **Send Notification** → broadcast to all students or target one;
     confirm it shows up in the student's **Notifications** inbox, and
     that a *different* student does NOT see a targeted one meant for
     someone else.
   - As a student, try hitting `/security/admin/threats/`,
     `/accounts/users/`, or `/notifications/send/` directly → all return a
     hard 403, not a redirect.

## Common bugs to watch for
- **`django.db.utils.OperationalError: (2002, ...)`** — MySQL isn't running
  or `DB_HOST`/`DB_PORT` are wrong.
- **`ModuleNotFoundError: MySQLdb`** — `mysqlclient` needs OS-level build deps
  (`libmysqlclient-dev` / `default-libmysqlclient-dev` on Debian/Ubuntu,
  `mysql-devel` on RHEL) before `pip install` will succeed.
- **CSRF 403 on every POST** — almost always means the CSRF token you're
  submitting doesn't match the one issued for the current session (stale
  page, wrong cookie jar, or — as I hit while smoke-testing this milestone —
  a regex/script bug grabbing the wrong token, not an app bug). Always fetch
  the form fresh before posting.
- **Chart.js shows nothing / console error "Unexpected token"** — if you
  ever change `admin_analytics` to pass a queryset straight into the
  template with `|safe`, it renders as Python dict repr (single quotes),
  which is not valid JSON. Always `json.dumps(list(queryset))` first.
- **Broadcast notification "read" state looks shared across users** — by
  design, `is_read` is only tracked for targeted notifications; broadcasts
  don't have per-user read receipts in this milestone (see Future
  Improvements).
- **Migrations conflict after model edits** — always run `makemigrations`
  and commit the resulting file; never hand-edit a migration that's already
  been applied to a shared DB.

## Interview questions this milestone maps to
- Why does `role_redirect` exist instead of setting `LOGIN_REDIRECT_URL`
  directly to two different places?
- How do the function-based `role_required` decorator and the class-based
  `AdminRequiredMixin` share logic instead of duplicating the role check?
- Why is file-extension/size validation done in the form's `clean_file`
  instead of the view — and why is it *not* treated as a real security
  control?
- Why does `Notification.recipient=None` mean "broadcast" instead of a
  separate `is_broadcast` boolean field?
- What's the tradeoff of storing `ScanLog.file` on local disk right now
  versus object storage, and when does that tradeoff bite?
- Why pass `json.dumps(...)` into the template instead of letting Django
  serialize the queryset automatically?

## Future improvements (deliberately deferred)
- Per-recipient read receipts on broadcast notifications (would need a
  `NotificationRead` through-table — not needed for this milestone's UI).
- Actual scan results (Milestone 3: FastAPI scanning engine + Milestone 5:
  wiring it to flip `ScanLog.status` off `PENDING`).
- PDF report generation (Milestone 4: Flask).
- Rate limiting on scan submission endpoints (Milestone 5 hardening).
- Split settings into base/dev/prod once Render/Vercel envs exist
  (Milestone 6).
- Object storage for uploaded files instead of local disk (Milestone 6,
  since Render's filesystem isn't persistent across deploys).

## Suggested git workflow
- Branch: `feature/milestone-2-dashboard-frontend`
- Commit message:
  `feat(dashboard): student/admin panels, threat intel CRUD, notifications, analytics`

