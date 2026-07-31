# CyberShield X

AI-Powered Cybersecurity Monitoring & Threat Intelligence Dashboard.

Multi-service project: Django, FastAPI, and (starting Milestone 4) Flask
each own a distinct slice of functionality but share one MySQL database.
No service has its own private schema — Django's migrations are the single
source of truth for table structure; the other services read/write those
same tables directly.

## Services

| Service | Directory | Owns |
|---|---|---|
| Django | `django-service/` | Auth, roles, session-based dashboard UI, security logs (schema owner), threat intel CRUD UI, notifications |
| FastAPI | `fastapi-service/` | File/URL scanning, password strength API, threat intel lookup API, security score API, AI assistant |
| Flask | `flask-service/` | PDF reports, email notifications, CSV export, analytics, log analysis |

## Why this split
- **Django** is the only service with a browser-facing UI and the only one
  that needs full session/CSRF machinery — a natural fit for
  request/response, form-heavy work (auth, admin CRUD, dashboards).
- **FastAPI** handles the parts that benefit from being a fast, stateless,
  independently-scalable API: scanning is bursty and CPU-light-but-latency-
  sensitive, exactly what an async framework is good at.
- **Flask** (Milestone 4) will handle background/utility work (PDF
  generation, email, CSV export) that doesn't need either Django's ORM
  machinery or FastAPI's async request model — a lightweight service is
  the right size for that job.

## Authentication across services
- Django owns real user accounts and issues JWTs via
  `POST /accounts/api/token/` (username + password → signed token).
- FastAPI (and Flask, from Milestone 4) verify that JWT using a shared
  `JWT_SECRET` — they never issue their own tokens and never see a raw
  password.
- The browser dashboard itself still uses Django's session cookie, not a
  JWT — JWTs are for service-to-service and any future non-browser client
  (mobile app, CLI, etc).

## Local development
Each service has its own `README.md`, `.env.example`, and
`requirements.txt` — they're independently installable. For local dev
without a MySQL server, `django-service`, `fastapi-service`, and
`flask-service` all support pointing at the same SQLite file
(`DB_ENGINE=sqlite3` / `SQLITE_PATH`) — see each service's README for
exact steps. In any real deployment, set `DB_ENGINE=mysql` in all three
and point them at the same MySQL instance.

`flask-service` also writes generated PDFs directly into
`django-service/media/reports/`, which only works because both services
are on the same filesystem in local dev / a single-host deployment. This
is flagged in `flask-service`'s README as something Milestone 6 needs to
replace with object storage once the services are deployed to separate
hosts (Render doesn't guarantee shared, persistent disk between services).

## Milestone status
- ✅ Milestone 1 — Django auth foundation
- ✅ Milestone 2 — Dashboard frontend, student/admin panels
- ✅ Milestone 3 — FastAPI scanning & intelligence APIs
- ✅ Milestone 4 — Flask reports, email, export, analytics
- ✅ Milestone 5 — Full integration (see `MILESTONE_5_INTEGRATION.md`)
- ✅ Milestone 6 — Deployment (see `DEPLOYMENT.md`)

## Deploying this project
See `DEPLOYMENT.md` for the full guide: Render Blueprint setup, external
MySQL provisioning (Render has no managed MySQL), S3-compatible object
storage for cross-service file sharing, environment variables, and a
post-deploy verification checklist. It also explains honestly why Vercel
isn't part of this deployment — the short version is there's no
standalone frontend build for it to host.

## Installation guide (local development)

Requirements: Python 3.11+, and either a local MySQL server or nothing at
all (all three services support `DB_ENGINE=sqlite3` for local dev, all
pointed at the same file).

```bash
git clone <this-repo>
cd cybershield-x

# 1. Django
cd django-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # set SECRET_KEY, JWT_SECRET, DB_ENGINE=sqlite3
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver              # :8000

# 2. FastAPI (new terminal)
cd fastapi-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # JWT_SECRET must match django-service exactly
uvicorn app.main:app --reload --port 8001

# 3. Flask (new terminal)
cd flask-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # JWT_SECRET must match; MEDIA_ROOT=../django-service/media
python run.py                            # :8002
```

Visit `http://127.0.0.1:8000/`, register a student account, and every
feature described in each service's README should work end to end. Each
service also has its own test suite (`manage.py test` / `pytest`) — 68
tests total across all three, all passing on a clean checkout.

## Running the full stack
See `MILESTONE_5_INTEGRATION.md` for exact setup and testing steps across
all three services. Short version: each service needs its own `.env`
(copied from `.env.example`) with a matching `JWT_SECRET` and the same
database, then `manage.py runserver` / `uvicorn app.main:app` / `python
run.py` in three terminals.
