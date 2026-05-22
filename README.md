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
python.exe -m pytest -q
```

Current result:

```text
16 passed
```

Also checked:

- API root responds.
- Dashboard metrics endpoint responds.
- Frontend is served at `/app/index.html`.
- No Supabase keys are hardcoded in source files.
- GitHub Actions CI is configured in `.github/workflows/ci.yml`.

## Requirements

- Python 3.11 or newer.
- pip.
- Supabase project for Vercel/public deployments.
- Optional SMTP account for real email sending.

## Local Setup

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Create your local environment file:

```bash
cp backend/config.example.env backend/config.env
```

Edit `backend/config.env` with your local values. Never commit real credentials.

Relevant environment variables:

```bash
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true
DEMO_MODE=true
SCRAPER_ALLOW_FALLBACKS=true
AUTH_ENABLED=false
AUTH_USERNAME=admin
AUTH_PASSWORD=
AUTH_SECRET_KEY=
AUTH_TOKEN_TTL_MINUTES=720
AUTH_COOKIE_SECURE=false

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
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/app/index.html
```

API docs:

```text
http://localhost:8000/docs
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

AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=use-a-long-random-password
AUTH_SECRET_KEY=use-a-long-random-secret
AUTH_COOKIE_SECURE=true

DEMO_MODE=false
SCRAPER_ALLOW_FALLBACKS=false
CORS_ALLOWED_ORIGINS=https://your-project.vercel.app
```

Run `supabase_schema.sql` in Supabase before the first deploy. Create a Supabase Storage bucket named `jobhunter-documents` if you want document upload/download to work in production. Without Supabase Storage, Vercel should not be treated as durable document storage.

Local Vercel smoke test:

```bash
npm i -g vercel
vercel dev
```

## Authentication

Authentication is optional and disabled by default for local demos. For any public or shared deployment, enable it:

```bash
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=use-a-long-random-password
AUTH_SECRET_KEY=use-a-long-random-secret
AUTH_COOKIE_SECURE=true
```

The login issues an HMAC-signed session token and an HTTP-only cookie. This is intended for single-user/private deployments. It is not a full multi-tenant identity system.

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
pytest
```

On Windows, if dependencies are installed in the Windows Python environment:

```bash
python.exe -m pytest -q
```

## Supabase Setup

1. Create a Supabase project.
2. Run `supabase_schema.sql` in the Supabase SQL Editor.
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

frontend/
  index.html
  *.png

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
pytest
git status --short
```

Make sure `backend/config.env`, `.env*`, `*.db`, `*.log`, uploaded documents, and generated caches are not staged.

## License

MIT
