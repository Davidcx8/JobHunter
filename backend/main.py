"""
JobHunter Pro - Backend API
Sistema de captación laboral con scraping inteligente y base de datos híbrida (SQLite + Supabase)
"""

import os
import re
import hmac
import json
import base64
import hashlib
import secrets
from pathlib import Path as FsPath
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Body, Path, Query, File, UploadFile, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import core modules
from db_manager import DatabaseManager
from matching_engine import MatchingEngine
from integrations import EmailDispatcher, WebhookDispatcher
from settings import settings

settings.require_valid_runtime_configuration()

# Scraper imports
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.indeed_scraper import IndeedScraper
from scrapers.remotive_scraper import RemotiveScraper
from scrapers.weworkremotely_scraper import WeWorkRemotelyScraper
from scrapers.glassdoor_scraper import GlassdoorScraper
from scrapers.ziprecruiter_scraper import ZipRecruiterScraper

# Initialize database manager
db = DatabaseManager(db_path=str(settings.resolved_db_path))

app = FastAPI(
    title="JobHunter Pro API",
    version="4.0.0",
    description="API híbrida (SQLite + Supabase) con Scraping Inteligente y Matching de Candidatos"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response

FRONTEND_DIR = FsPath(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
}


def safe_upload_filename(filename: str) -> str:
    name = FsPath(filename or "document").name.strip()
    cleaned = SAFE_FILENAME_RE.sub("_", name).strip("._")
    return cleaned or "document"


def validate_upload(file: UploadFile) -> str:
    filename = safe_upload_filename(file.filename or "")
    suffix = FsPath(filename).suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")
    return filename


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_auth_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.auth_token_ttl_minutes)).timestamp()),
        "nonce": secrets.token_urlsafe(12),
    }
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_raw)
    signature = hmac.new(
        settings.resolved_auth_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_b64url_encode(signature)}"


def verify_auth_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or "." not in token:
        return None
    payload_b64, signature_b64 = token.rsplit(".", 1)
    expected = hmac.new(
        settings.resolved_auth_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        provided = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected, provided):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        return None
    if payload.get("sub") != settings.auth_username:
        return None
    return payload


def extract_auth_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.cookies.get("jobhunter_session")


class LoginRateLimiter:
    def __init__(self) -> None:
        self._failures: Dict[str, Dict[str, float]] = {}

    def _key(self, request: Request, username: str) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        client_host = forwarded_for or (request.client.host if request.client else "unknown")
        return f"{client_host}:{username.strip().lower()}"

    def is_limited(self, request: Request, username: str) -> bool:
        if settings.auth_login_max_failures < 1:
            return False
        key = self._key(request, username)
        record = self._failures.get(key)
        if not record:
            return False
        locked_until = record.get("locked_until", 0)
        now = datetime.now(timezone.utc).timestamp()
        if locked_until > now:
            return True
        if locked_until:
            self._failures.pop(key, None)
        return False

    def record_failure(self, request: Request, username: str) -> None:
        if settings.auth_login_max_failures < 1:
            return
        key = self._key(request, username)
        record = self._failures.setdefault(key, {"count": 0, "locked_until": 0})
        record["count"] += 1
        if record["count"] >= settings.auth_login_max_failures:
            record["locked_until"] = (
                datetime.now(timezone.utc).timestamp() + settings.auth_login_lockout_seconds
            )

    def record_success(self, request: Request, username: str) -> None:
        self._failures.pop(self._key(request, username), None)

    def reset(self) -> None:
        self._failures.clear()


login_rate_limiter = LoginRateLimiter()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    public_paths = (
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/config",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/session",
        "/api/health",
        "/api/ready",
        "/app",
    )

    if path.startswith("/api/") and not path.startswith("/api/auth/") and db.storage_status == "supabase_unavailable":
        if path not in {"/api/health", "/api/ready"}:
            return Response(
                content=json.dumps({"detail": "STORAGE_BACKEND=supabase but Supabase is not configured or unavailable."}),
                status_code=503,
                media_type="application/json",
            )

    if not settings.auth_enabled:
        return await call_next(request)

    if path == "/" or any(path.startswith(public_path) for public_path in public_paths if public_path != "/"):
        return await call_next(request)

    if not settings.auth_configured:
        return Response(
            content=json.dumps({"detail": "Authentication is enabled but AUTH_PASSWORD and AUTH_SECRET_KEY are not configured."}),
            status_code=503,
            media_type="application/json",
        )

    token = extract_auth_token(request)
    if not token or not verify_auth_token(token):
        return Response(
            content=json.dumps({"detail": "Authentication required."}),
            status_code=401,
            media_type="application/json",
        )

    return await call_next(request)

# ==================== PYDANTIC SCHEMAS ====================

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    cv_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    social_links: Optional[List[Dict[str, str]]] = None
    skills: Optional[List[str]] = None
    experience: Optional[str] = None
    education: Optional[str] = None

class JobCreate(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Remote"
    url: str
    source: Optional[str] = "manual"
    description: Optional[str] = ""
    requirements: Optional[str] = ""
    salary: Optional[str] = None
    company_rating: Optional[str] = None
    posted_date: Optional[str] = None
    status: Optional[str] = "new"
    is_live: Optional[bool] = True
    scrape_mode: Optional[str] = "live"
    scraped_at: Optional[str] = None

class JobUpdate(BaseModel):
    status: Optional[str] = None
    match_score: Optional[float] = None

class ContactCreate(BaseModel):
    name: str
    email: str
    company: Optional[str] = ""
    role: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    notes: Optional[str] = ""

class ApplicationCreate(BaseModel):
    job_id: Optional[int] = None
    company: str
    position: str
    applied_date: Optional[str] = None
    status: Optional[str] = "applied"
    follow_up_date: Optional[str] = None
    notes: Optional[str] = ""

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    follow_up_date: Optional[str] = None
    notes: Optional[str] = None

class ScrapeRequest(BaseModel):
    keywords: str = ""
    location: str = "remote"
    limit: int = 20

class SendEmailRequest(BaseModel):
    contact_email: str
    subject: str
    body: str

class LoginRequest(BaseModel):
    username: str
    password: str

# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "status": "online",
        "database": "sqlite_hybrid",
        "supabase_connected": db.supabase_client is not None,
        "storage_backend": db.storage_status,
        "document_storage": "supabase" if db.uses_supabase_storage else "local",
        "demo_mode": settings.demo_mode,
        "scraper_fallbacks_enabled": settings.scraper_allow_fallbacks,
        "auth_enabled": settings.auth_enabled,
        "auth_configured": settings.auth_configured,
    }

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
        "storage_backend": db.storage_status,
    }

@app.get("/api/ready")
async def ready():
    issues = []
    if db.storage_status == "supabase_unavailable":
        issues.append("Supabase is not configured or unavailable.")
    if settings.auth_enabled and not settings.auth_configured:
        issues.append("Authentication is enabled but not fully configured.")

    if issues:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "issues": issues,
                "storage_backend": db.storage_status,
            },
        )

    return {
        "status": "ready",
        "storage_backend": db.storage_status,
        "auth_enabled": settings.auth_enabled,
    }

@app.get("/api/auth/config")
async def auth_config():
    return {
        "auth_enabled": settings.auth_enabled,
        "auth_configured": settings.auth_configured,
        "username_hint": settings.auth_username if settings.auth_enabled else None,
    }

@app.post("/api/auth/login")
async def login(payload: LoginRequest, response: Response, request: Request):
    if not settings.auth_enabled:
        return {"success": True, "auth_enabled": False}
    if not settings.auth_configured:
        raise HTTPException(status_code=503, detail="Authentication is not fully configured.")
    if login_rate_limiter.is_limited(request, payload.username):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")

    valid_user = hmac.compare_digest(payload.username, settings.auth_username)
    valid_password = hmac.compare_digest(payload.password, settings.auth_password)
    if not valid_user or not valid_password:
        login_rate_limiter.record_failure(request, payload.username)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    login_rate_limiter.record_success(request, payload.username)
    token = create_auth_token(settings.auth_username)
    response.set_cookie(
        key="jobhunter_session",
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_token_ttl_minutes * 60,
        path="/",
    )
    payload = {"success": True, "expires_in": settings.auth_token_ttl_minutes * 60}
    if settings.auth_return_bearer_token:
        payload["token"] = token
    return payload

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("jobhunter_session", path="/")
    return {"success": True}

@app.get("/api/auth/session")
async def session(request: Request):
    if not settings.auth_enabled:
        return {"authenticated": True, "auth_enabled": False}
    token = extract_auth_token(request)
    payload = verify_auth_token(token or "")
    return {
        "authenticated": payload is not None,
        "auth_enabled": True,
        "username": payload.get("sub") if payload else None,
    }

# --- Profile Endpoints ---
@app.get("/api/profile")
async def get_profile():
    profile = db.get_profile()
    return {"profile": profile}

@app.post("/api/profile")
async def update_profile(profile_data: ProfileUpdate):
    updated = db.save_profile(profile_data.model_dump(exclude_unset=True))
    
    # After saving profile, recompute match scores for all 'new' jobs dynamically
    try:
        profile = db.get_profile()
        user_skills = profile.get("skills", [])
        if user_skills:
            all_new_jobs = db.get_jobs(status="new", limit=500)
            for job in all_new_jobs:
                score, matching, missing = MatchingEngine.calculate_score(
                    job.get("title", ""),
                    job.get("description", ""),
                    job.get("requirements", ""),
                    user_skills
                )
                db.update_job(job.get("id"), match_score=score)
    except Exception as e:
        print(f"Error recalculating job match scores: {e}")
        
    return {"success": True, "profile": updated}

# --- Jobs Endpoints ---
@app.get("/api/jobs")
async def get_jobs(
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100)
):
    jobs = db.get_jobs(source=source, status=status, limit=limit)
    return {"jobs": jobs}

@app.post("/api/jobs")
async def create_job(job_data: JobCreate):
    job_dict = job_data.model_dump()
    
    # 1. Fetch user skills to compute match score
    profile = db.get_profile()
    user_skills = profile.get("skills", [])
    
    # 2. Calculate match score
    score, matching, missing = MatchingEngine.calculate_score(
        job_dict.get("title", ""),
        job_dict.get("description", ""),
        job_dict.get("requirements", ""),
        user_skills
    )
    job_dict["match_score"] = score
    
    # 3. Save to database
    saved_job = db.add_job(job_dict)
    
    # 4. Trigger Webhook/Telegram alert if high match score
    if score >= 80.0:
        WebhookDispatcher.send_notification(saved_job)
        
    return {"success": True, "job": saved_job}

@app.put("/api/jobs/{job_id}")
async def update_job(
    job_id: int = Path(...),
    payload: JobUpdate = Body(None),
    status: Optional[str] = Query(None),
    match_score: Optional[float] = None
):
    """
    Updates job status and/or match score.
    Supports BOTH Pydantic JSON Body (modern SPA) and Query parameters (legacy API calls).
    """
    # Prefer body payload values if present
    status_val = payload.status if payload and payload.status is not None else status
    score_val = payload.match_score if payload and payload.match_score is not None else match_score
    
    updated = db.update_job(job_id, status=status_val, match_score=score_val)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # If status becomes 'applied', auto-create an Application entry
    if status_val == 'applied':
        try:
            # Check if application already exists for this job
            existing = db.get_applications()
            if not any(app.get("job_id") == job_id for app in existing):
                db.add_application({
                    "job_id": job_id,
                    "company": updated.get("company", "N/A"),
                    "position": updated.get("title", "N/A"),
                    "status": "applied",
                    "notes": f"Automatic application entry via status update."
                })
        except Exception as e:
            print(f"Error auto-creating application card: {e}")
            
    return {"success": True, "job": updated}

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: int):
    success = db.delete_job(job_id)
    return {"success": success}

# --- Contacts Endpoints ---
@app.get("/api/contacts")
async def get_contacts(limit: int = 100):
    contacts = db.get_contacts(limit=limit)
    return {"contacts": contacts}

@app.post("/api/contacts")
async def create_contact(contact_data: ContactCreate):
    saved = db.add_contact(contact_data.model_dump())
    return {"success": True, "contact": saved}

# --- Applications Endpoints ---
@app.get("/api/applications")
async def get_applications(status: Optional[str] = Query(None)):
    apps = db.get_applications(status=status)
    return {"applications": apps}

@app.post("/api/applications")
async def create_application(app_data: ApplicationCreate):
    saved = db.add_application(app_data.model_dump())
    return {"success": True, "application": saved}

@app.put("/api/applications/{app_id}")
async def update_application(app_id: int, app_data: ApplicationUpdate):
    updated = db.update_application(
        app_id,
        status=app_data.status,
        follow_up_date=app_data.follow_up_date,
        notes=app_data.notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"success": True, "application": updated}

@app.delete("/api/applications/{app_id}")
async def delete_application(app_id: int):
    success = db.delete_application(app_id)
    if not success:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"success": True}

# --- Dashboard Endpoints ---
@app.get("/api/dashboard")
async def get_dashboard():
    stats = db.get_dashboard_metrics()
    return stats

# --- Scraping Route ---
@app.post("/api/scrape/{source}")
async def scrape_jobs(
    source: str = Path(...),
    req: ScrapeRequest = Body(...)
):
    source_lower = source.lower()
    
    # Instantiate correct scraper
    if source_lower == "linkedin":
        scraper = LinkedInScraper()
    elif source_lower == "indeed":
        scraper = IndeedScraper()
    elif source_lower == "remotive":
        scraper = RemotiveScraper()
    elif source_lower == "weworkremotely":
        scraper = WeWorkRemotelyScraper()
    elif source_lower == "glassdoor":
        scraper = GlassdoorScraper()
    elif source_lower == "ziprecruiter":
        scraper = ZipRecruiterScraper()
    else:
        raise HTTPException(status_code=400, detail=f"Source '{source}' is not supported.")
        
    try:
        found_jobs = scraper.search(keywords=req.keywords, limit=req.limit)
        now = datetime.now().isoformat()
        for job in found_jobs:
            job.setdefault("is_live", True)
            job.setdefault("scrape_mode", "live" if job.get("is_live") else "demo")
            job.setdefault("scraped_at", now)

        live_jobs = [job for job in found_jobs if job.get("is_live")]
        fallback_jobs = [job for job in found_jobs if not job.get("is_live")]
        if fallback_jobs and not settings.scraper_allow_fallbacks:
            found_jobs = live_jobs

        return {
            "source": source_lower,
            "jobs_found": len(found_jobs),
            "live_jobs": len([job for job in found_jobs if job.get("is_live")]),
            "fallback_jobs": len([job for job in found_jobs if not job.get("is_live")]),
            "fallbacks_allowed": settings.scraper_allow_fallbacks,
            "jobs": found_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during scraping process: {str(e)}")

# --- Outreach Email Endpoint ---
@app.post("/api/email/send")
async def send_email(req: SendEmailRequest):
    result = EmailDispatcher.send_email(
        to_email=req.contact_email,
        subject=req.subject,
        body_html=req.body
    )
    
    if result.get("success"):
        # Log email count and date inside contacts
        db.increment_sent_emails(req.contact_email)
        
        db.add_email_log(
            contact_email=req.contact_email,
            subject=req.subject,
            body=req.body,
            status=result.get("status", "sent"),
        )
            
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to dispatch email."))

@app.get("/api/emails")
async def get_emails(contact_id: Optional[int] = Query(None)):
    return {"success": True, "emails": db.get_emails(contact_id=contact_id)}

# ==================== DOCUMENTS CONTROLLER ====================

@app.post("/api/documents")
async def upload_document(
    name: str = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...)
):
    filename = validate_upload(file)

    # Read file with an explicit size cap before choosing the storage target.
    bytes_written = 0
    chunks = []
    while chunk := await file.read(1024 * 1024):
        bytes_written += len(chunk)
        if bytes_written > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size is {settings.max_upload_mb}MB.",
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    file_url = None
    if db.uses_supabase_storage:
        storage_path = f"documents/{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_urlsafe(6)}-{filename}"
        try:
            db.supabase_client.storage.from_(settings.supabase_storage_bucket).upload(
                storage_path,
                file_bytes,
                file_options={
                    "content-type": file.content_type or "application/octet-stream",
                    "upsert": "true",
                },
            )
            try:
                file_url = db.supabase_client.storage.from_(settings.supabase_storage_bucket).get_public_url(storage_path)
            except Exception:
                file_url = None
            file_path = f"supabase://{settings.supabase_storage_bucket}/{storage_path}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload file to Supabase Storage: {str(e)}")
    else:
        upload_dir = settings.resolved_upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        if db.storage_status == "supabase":
            raise HTTPException(
                status_code=503,
                detail="Supabase Storage is not configured. Set SUPABASE_STORAGE_BUCKET or use local SQLite storage.",
            )
        try:
            with file_path.open("wb") as buffer:
                buffer.write(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Save meta to DB
    doc_data = {
        "name": name,
        "filename": filename,
        "file_type": file_type,
        "file_path": str(file_path),
        "file_url": file_url,
        "file_size": bytes_written
    }
    
    saved_doc = db.add_document(doc_data)
    return {"success": True, "document": saved_doc}

@app.get("/api/documents")
async def get_documents():
    docs = db.get_documents()
    return {"success": True, "documents": docs}

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    file_path = doc.get("file_path")
    if file_path and str(file_path).startswith("supabase://") and db.uses_supabase_storage:
        storage_path = str(file_path).split("/", 3)[-1]
        try:
            db.supabase_client.storage.from_(settings.supabase_storage_bucket).remove([storage_path])
        except Exception as e:
            print(f"Warning: failed to delete file from Supabase Storage: {e}")
    elif file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: failed to delete file from disk: {e}")
            
    # Delete from DB
    deleted = db.delete_document(doc_id)
    if deleted:
        return {"success": True, "message": "Document deleted successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete document from database.")

@app.get("/api/documents/download/{doc_id}")
async def download_document(doc_id: int):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    file_path = doc.get("file_path")
    if file_path and str(file_path).startswith("supabase://") and db.uses_supabase_storage:
        storage_path = str(file_path).split("/", 3)[-1]
        try:
            payload = db.supabase_client.storage.from_(settings.supabase_storage_bucket).download(storage_path)
            return StreamingResponse(
                iter([payload]),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{doc.get("filename")}"'},
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"File not found in Supabase Storage: {str(e)}")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file not found on disk.")

    resolved_path = FsPath(file_path).resolve()
    upload_root = settings.resolved_upload_dir.resolve()
    if upload_root not in resolved_path.parents and resolved_path != upload_root:
        raise HTTPException(status_code=403, detail="Document path is outside the upload directory.")
        
    return FileResponse(
        path=str(resolved_path),
        filename=doc.get("filename"),
        media_type="application/octet-stream"
    )

if __name__ == "__main__":
    import uvicorn
    # Default local dev port
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=settings.api_debug)
