# Deployment Guide (Milestone 6)

## Before you deploy: two things the original plan got wrong

**"Frontend: Vercel" doesn't apply here, and that's fine.** Vercel deploys
static sites and SPA builds (Next.js, React, etc). This project's frontend
is server-rendered Django templates — Bootstrap 5 + vanilla JS, rendered
by Django itself, which was the explicit design from Milestone 1 onward
("Django: HTML Rendering" in the original task split). There is no
separate frontend build artifact to hand to Vercel. Rather than force an
awkward split (e.g., extracting static assets to a Vercel-hosted CDN just
to say "Vercel is used"), Django serves its own static files in
production via WhiteNoise — one process, one deploy, no synchronization
problem between "the frontend" and "the backend" because there's only one
thing serving HTML. If you specifically want a CDN in front of static
assets for performance at scale, WhiteNoise's `Cache-Control` headers
already make Cloudflare (as a transparent proxy, not Vercel-the-platform)
a drop-in option later — not needed for this deployment.

**Render does not offer managed MySQL.** Render's native managed database
offerings are PostgreSQL and Redis. Since the brief specifies MySQL
explicitly (and all three services' ORMs are written against it), you
need an external MySQL provider. Any of these work — pick based on budget:
- **PlanetScale** (MySQL-compatible, generous free tier, easiest setup)
- **Railway** (straightforward MySQL, pay-as-you-go)
- **AWS RDS for MySQL** (most control, more setup)

Whichever you pick, you'll end up with a host, port, database name,
username, and password — that's what goes into `DB_HOST`/`DB_PORT`/
`DB_NAME`/`DB_USER`/`DB_PASSWORD` for all three services below.

## What actually deploys where

| Piece | Where | Why |
|---|---|---|
| django-service | Render (Web Service) | Owns the dashboard UI, serves its own static files |
| fastapi-service | Render (Web Service) | Stateless API, scales independently of Django |
| flask-service | Render (Web Service) | Same — independent scaling for report/email/export load |
| MySQL | External provider (see above) | Render has no managed MySQL |
| Uploaded files / generated PDFs | S3-compatible object storage | Render containers don't share a filesystem (see below) |

## The filesystem problem, and how this deployment solves it

Milestones 1–5 worked locally because `django-service` and `flask-service`
happened to run on the same machine and could share a `media/` directory
on disk. On Render, each Web Service is its own container — Flask writing
a PDF to "its" disk would be invisible to Django running in a different
container. **This is solved, not just documented**: both services support
`USE_S3=True`, which switches Django to `django-storages`' S3 backend and
Flask to uploading generated PDFs directly to the same bucket via `boto3`,
using the identical `reports/<uuid>.pdf` key convention both sides already
agreed on back in Milestone 4. Point both at the same bucket and
credentials and file sharing works correctly across separate containers.

Any S3-compatible provider works — set `AWS_S3_ENDPOINT_URL` for
non-AWS options (Cloudflare R2, Backblaze B2, DigitalOcean Spaces all
have free/cheap tiers); leave it unset for real AWS S3.

**Verification note:** the S3 code path is tested against a mocked
`boto3` client (`flask-service/app/tests/test_s3_storage.py`) — this
sandbox's network egress doesn't reach AWS/S3-compatible endpoints, so it
was not possible to verify against a real bucket here. Test it against
your actual bucket before trusting it in production: generate a report
with `USE_S3=True` pointed at a real bucket, confirm the object appears,
and confirm Django's `report.file.url` resolves to it.

## Step-by-step: Render Blueprint deploy

1. **Provision MySQL** with your chosen external provider. Create the
   database; note host/port/name/user/password.
2. **Create an S3-compatible bucket** (or reuse one). Note the bucket
   name, region, access key, secret key, and endpoint URL (if not AWS).
3. **Generate a `JWT_SECRET`** — any long random string. It must be
   identical across all three services; nothing auto-generates it because
   drift between services breaks every cross-service call. `python -c
   "import secrets; print(secrets.token_urlsafe(48))"` works fine.
4. **Push this repo to GitHub** (or GitLab) if you haven't already —
   Render Blueprints deploy from a connected repo.
5. In the Render dashboard: **New → Blueprint**, point it at this repo.
   Render reads `render.yaml` at the root and proposes all three services.
6. Render will prompt for every `sync: false` env var in `render.yaml` —
   fill in the MySQL credentials, `JWT_SECRET` (same value, all three
   services), the S3/AWS credentials (same value, django + flask), and
   the placeholder URLs (`ALLOWED_HOSTS`, `FASTAPI_BASE_URL`,
   `FLASK_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`) —
   Render shows you each service's assigned `.onrender.com` URL as you go,
   so you can fill these in correctly even though they reference each
   other.
7. Deploy. Render runs each service's `buildCommand` (Django's includes
   `collectstatic` and `migrate`) then `startCommand`.
8. **Create your first admin** — Render's dashboard has a Shell tab per
   service; on `cybershield-x-django`, run `python manage.py
   createsuperuser`, then promote that user to `Role.ADMIN` via Django
   admin at `/admin/` (superuser status and the app's own `role` field are
   intentionally separate — see `apps/accounts/models.py`'s docstring from
   Milestone 1).

## Environment variable reference

Full details and defaults are in each service's `.env.example`. The ones
that **must match exactly** across services:

| Variable | Must match across |
|---|---|
| `JWT_SECRET` | All three services |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_STORAGE_BUCKET_NAME` / `AWS_S3_REGION_NAME` / `AWS_S3_ENDPOINT_URL` | django-service + flask-service (fastapi-service doesn't touch files) |
| `DB_*` | All three services (same database) |

## Post-deploy verification checklist

Run through this after every deploy — it's the same live smoke test used
throughout Milestones 3–5, just against real URLs instead of localhost:

1. Visit the Django URL → login page loads, styled correctly (confirms
   WhiteNoise is serving static files).
2. Register a student, log in → dashboard loads with a security score
   widget (confirms Django → FastAPI over real HTTPS).
3. Submit a URL scan → Scan History shows a real verdict within a few
   seconds, not stuck at PENDING (confirms FastAPI is reachable and
   writing to the same MySQL database Django reads).
4. Generate a report → downloads a real PDF (confirms Flask → S3 upload
   → Django's S3-backed `FileField` serving all agree on the same
   object).
5. As an admin, send a broadcast notification → check the recipient's
   real inbox if SMTP is configured, or check `flask-service`'s Render
   logs for the console-fallback entry if not.
6. Export a CSV from any export button → downloads real data.

If any step fails, check that service's Render logs first — every
integration failure in Django surfaces as a specific, non-generic
"service unavailable" message (see `apps/integrations/exceptions.py`),
which should point you at which of the three services to check.

## Rollback / troubleshooting

- **500 on every Django page** — almost always `collectstatic` or
  `migrate` failing in the build step; check the build logs, not the
  runtime logs.
- **Every cross-service call fails** — `JWT_SECRET` mismatch; check all
  three services' env vars byte-for-byte.
- **Reports generate but won't download** — S3 credentials/bucket
  mismatch between django-service and flask-service, or a bucket policy
  blocking the presigned URL flow (flask-service generates a 5-minute
  presigned URL and redirects to it — confirm the bucket allows
  `GetObject` for the credentials in use).
- **Scans stuck at PENDING in production** — `FASTAPI_BASE_URL` on
  django-service is wrong or fastapi-service is down; check
  fastapi-service's Render logs and confirm its `/health` endpoint
  responds.
