# JobHunter Pro

JobHunter Pro is a local-first job search command center for tracking opportunities, recruiter contacts, applications, outreach emails, documents, and candidate-job match scores.

The project ships with a FastAPI backend, SQLite local storage for development, Supabase-backed production storage, resilient job scrapers, and a static dashboard UI served by the backend.

## Features

- Job catalog with status tracking and match scores.
- Candidate profile used by the matching engine, including core links plus additional social/profile URLs.
- Recruiter/contact CRM with outreach history.
- Application pipeline with Kanban-style status columns.
- Document vault for CVs, certificates, cover letters, and portfolio files.
- Email outreach through SMTP, with dry-run mode when SMTP is not configured.
- Optional webhook alerts for high-match jobs.
- Supabase primary storage mode for Vercel/public deployments.
- Optional Supabase Storage support for uploaded documents.
- Local SQLite fallback for development and offline usage.
- Explicit `LIVE` vs `DEMO` source labeling so fallback rows are not confused with verified live vacancies.
- Optional single-user login for local/private deployments.

## Scraping Sources

Implemented sources:

```text
linkedin
indeed
remotive
weworkremotely
glassdoor
ziprecruiter
```

Not implemented yet:

```text
upwork
fiverr
freelancer
workana
```

Some sources may block or rate-limit scraping. When that happens, the scraper returns deterministic demo fallback data so the product flow remains testable. Do not present fallback rows as verified live vacancies.

Set `SCRAPER_ALLOW_FALLBACKS=false` if you want blocked sources to return zero results instead of demo fallback rows.

## Current Validation

Validated locally with:

```bash
python3 -m pytest -q
```

Current result:

```text
25 passed
```

Also checked:

- API root, `/api/health`, and `/api/ready` respond.
- Dashboard metrics endpoint responds.
- Frontend is served at `/app/index.html`.
- No Supabase keys are hardcoded in source files.
- GitHub Actions CI is configured in `.github/workflows/ci.yml`.
- `pip-audit` reports no known vulnerable Python dependencies.

## Requirements

- Python 3.11 or newer.
- pip.
- Supabase project for Vercel/public deployments.
- Optional SMTP account for real email sending.

## Local Setup

Create an isolated Python environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
```

Create your local environment file:

```bash
cp backend/config.example.env backend/config.env
```

Edit `backend/config.env` with your local values. Never commit real credentials.

Relevant environment variables:

```bash
API_HOST=127.0.0.1
API_PORT=8000
APP_ENV=development
API_DEBUG=true
DEMO_MODE=true
SCRAPER_ALLOW_FALLBACKS=true
AUTH_ENABLED=false
AUTH_USERNAME=admin
AUTH_PASSWORD=
AUTH_SECRET_KEY=
AUTH_TOKEN_TTL_MINUTES=720
AUTH_COOKIE_SECURE=false
AUTH_RETURN_BEARER_TOKEN=false
AUTH_LOGIN_MAX_FAILURES=5
AUTH_LOGIN_LOCKOUT_SECONDS=300

STORAGE_BACKEND=sqlite
DB_PATH=./data/jobhunter.db
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_MB=10

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000,null

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
SUPABASE_STORAGE_BUCKET=jobhunter-documents

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=

NOTIFICATION_WEBHOOK=
TELEGRAM_CHAT_ID=
```

## Run

```bash
npm run dev
```

Open:

```text
http://localhost:8000/app/index.html
```

API docs:

```text
http://localhost:8000/docs
```

Health checks:

```text
http://localhost:8000/api/health
http://localhost:8000/api/ready
```

## Docker

Build and run:

```bash
docker build -t jobhunter-pro .
docker run --rm -p 8000:8000 --env-file backend/config.example.env jobhunter-pro
```

For real credentials, create a local env file and pass that instead of the example file.

## Vercel Deployment

This repo includes `vercel.json`, `api/index.py`, and a root `requirements.txt` so Vercel can run the FastAPI app as a Python serverless function. The UI is served by FastAPI at:

```text
https://your-project.vercel.app/app/index.html
```

Recommended production backend decision:

```text
Vercel = hosting/runtime
FastAPI = application API, scraping, matching, auth, email/webhooks
Supabase = persistent database and optional document storage
```

Use Supabase instead of Firebase for this version because the project already has Supabase schema, Python SDK integration, and backend-only secret handling. Firebase would be a larger migration and would not improve the current scraping/matching backend immediately.

Set these Vercel environment variables before publishing:

```bash
STORAGE_BACKEND=supabase
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=jobhunter-documents

APP_ENV=production
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=use-a-long-random-password
AUTH_SECRET_KEY=use-a-long-random-secret
AUTH_COOKIE_SECURE=true
AUTH_RETURN_BEARER_TOKEN=false

DEMO_MODE=false
SCRAPER_ALLOW_FALLBACKS=false
CORS_ALLOWED_ORIGINS=https://your-project.vercel.app
```

Apply the Supabase schema before the first deploy. Preferred path:

```bash
npx -y supabase login
npx -y supabase link --project-ref your-project-ref
npx -y supabase db push --workdir .
```

Fallback path: run `supabase_schema.sql` in the Supabase SQL Editor.

Create a Supabase Storage bucket named `jobhunter-documents` if you want document upload/download to work in production. Without Supabase Storage, Vercel should not be treated as durable document storage.

Local Vercel smoke test:

```bash
npm i -g vercel
vercel dev
```

Production smoke test after deploy:

```bash
JOBHUNTER_BASE_URL=https://your-project.vercel.app \
AUTH_USERNAME=admin \
AUTH_PASSWORD=your-production-password \
python3 scripts/smoke_test.py
```

## Realistic Production Runbook

1. Create a Supabase project.
2. Apply migrations with `npx -y supabase db push --workdir .`, or run `supabase_schema.sql` in the SQL Editor.
3. Create the `jobhunter-documents` Storage bucket.
4. Copy `backend/config.production.example.env` into your hosting provider environment variables and replace every placeholder.
5. Validate the environment before deploy:

```bash
python3 scripts/production_check.py --env-file path/to/your-production.env
```

6. Deploy the FastAPI app.
7. Run the external smoke test:

```bash
JOBHUNTER_BASE_URL=https://your-domain.example \
AUTH_USERNAME=admin \
AUTH_PASSWORD=your-production-password \
python3 scripts/smoke_test.py
```

8. Open `/app/index.html`, log in, update your profile, add one manual job, upload one small document, and verify `/api/ready` returns `{"status":"ready"}`.

## Authentication

Authentication is optional and disabled by default for local demos. For any public or shared deployment, enable it:

```bash
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=use-a-long-random-password
AUTH_SECRET_KEY=use-a-long-random-secret
AUTH_COOKIE_SECURE=true
```

The login issues an HMAC-signed session token in an HTTP-only cookie. Bearer token responses are disabled by default to avoid persisting credentials in browser storage. This is intended for single-user/private deployments. It is not a full multi-tenant identity system.

When `APP_ENV=production`, startup validates the security-critical configuration and fails fast if authentication, secure cookies, CORS origins, or Supabase service-key requirements are unsafe.

## Candidate Links

The profile includes first-class fields for Portfolio, GitHub, and LinkedIn because they are common in technical hiring workflows. Additional links can be stored as `Label | URL` rows, for example:

```text
Calendly | https://calendly.com/example
Blog | https://example.com/blog
Behance | https://behance.net/example
```

This keeps the profile flexible without adding a new database column for every network.

## Tests

```bash
python3 -m pytest -q
```

On Windows, if dependencies are installed in the Windows Python environment:

```bash
python.exe -m pytest -q
```

## Supabase Setup

1. Create a Supabase project.
2. Apply `supabase/migrations/20260606180319_initial_schema.sql` with `npx -y supabase db push --workdir .`, or run `supabase_schema.sql` in the SQL Editor.
3. Create a Storage bucket named `jobhunter-documents` if document uploads are needed.
4. Set `STORAGE_BACKEND=supabase`.
5. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_KEY`.
6. Set `SUPABASE_SERVICE_KEY` only in trusted backend environments such as Vercel server-side variables.

If a Supabase service key was ever committed or published, treat it as exposed and rotate it in Supabase before using this project publicly.

## Email and Webhooks

Email sending uses SMTP. If `EMAIL_USER` or `EMAIL_PASSWORD` is missing, `/api/email/send` runs in dry-run mode and logs the outreach instead of sending a real email.

Webhook alerts use `NOTIFICATION_WEBHOOK` and trigger when a saved job reaches a high match score.

## API Overview

```text
GET    /api/health
GET    /api/ready

GET    /api/dashboard
GET    /api/auth/config
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/session

GET    /api/profile
POST   /api/profile

GET    /api/jobs
POST   /api/jobs
PUT    /api/jobs/{job_id}
DELETE /api/jobs/{job_id}

GET    /api/contacts
POST   /api/contacts

GET    /api/applications
POST   /api/applications
PUT    /api/applications/{app_id}
DELETE /api/applications/{app_id}

POST   /api/scrape/{source}

POST   /api/email/send
GET    /api/emails

GET    /api/documents
POST   /api/documents
DELETE /api/documents/{doc_id}
GET    /api/documents/download/{doc_id}
```

## Project Structure

```text
backend/
  main.py
  settings.py
  db_manager.py
  integrations.py
  matching_engine.py
  scheduler.py
  scrapers/
  config.example.env
  config.production.example.env

frontend/
  index.html
  *.png

scripts/
  production_check.py
  smoke_test.py

supabase/
  migrations/

tests/
supabase_schema.sql
```

## Public Repository Notes

The repository intentionally ignores:

- Local environment files.
- SQLite databases.
- Uploads.
- Logs.
- Python caches.
- Generated build output.

Before publishing:

```bash
python3 -m pytest -q
python3 scripts/production_check.py --env-file path/to/your-production.env
git status --short
```

Make sure `backend/config.env`, `.env*`, `*.db`, `*.log`, uploaded documents, and generated caches are not staged.

## License

MIT
