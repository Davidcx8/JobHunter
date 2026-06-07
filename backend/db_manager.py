import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase Python SDK not installed. Supabase features will be disabled.")

class DatabaseManager:
    def __init__(self, db_path: str = "./data/jobhunter.db"):
        self.db_path = db_path
        self.storage_backend = settings.storage_backend

        # Initialize Supabase if credentials are present
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        self.supabase_client: Optional[Client] = None
        if SUPABASE_AVAILABLE and self.supabase_url and (self.supabase_service_key or self.supabase_anon_key):
            try:
                key = self.supabase_service_key or self.supabase_anon_key
                self.supabase_client = create_client(self.supabase_url, key)
                logger.info("Supabase client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")

        if not self.uses_supabase_primary:
            # Ensure the directory exists if a local SQLite path is used.
            dir_name = os.path.dirname(self.db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            self.init_sqlite_tables()
            self.seed_mock_data_if_empty()

    @property
    def uses_supabase_primary(self) -> bool:
        if self.storage_backend == "supabase":
            return self.supabase_client is not None
        if self.storage_backend == "auto":
            return self.supabase_client is not None
        return False

    @property
    def storage_status(self) -> str:
        if self.uses_supabase_primary:
            return "supabase"
        if self.storage_backend == "supabase" and self.supabase_client is None:
            return "supabase_unavailable"
        return "sqlite"

    @property
    def uses_supabase_storage(self) -> bool:
        return bool(self.supabase_client and settings.supabase_storage_bucket and self.uses_supabase_primary)

    def _normalize_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(row)
        if "is_live" in normalized and normalized["is_live"] is not None:
            normalized["is_live"] = bool(normalized["is_live"])
        normalized.setdefault("social_links", [])
        normalized.setdefault("skills", [])
        return normalized

    def _supabase_required(self) -> Client:
        if not self.supabase_client:
            raise RuntimeError("Supabase is configured as primary storage but the client is unavailable.")
        return self.supabase_client

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_sqlite_tables(self):
        """Creates tables in SQLite if they do not exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # User Profiles
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                location TEXT,
                headline TEXT,
                bio TEXT,
                cv_url TEXT,
                portfolio_url TEXT,
                github_url TEXT,
                linkedin_url TEXT,
                social_links TEXT,
                skills TEXT,
                experience TEXT,
                education TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """)
            self._ensure_column(cursor, "user_profiles", "social_links", "TEXT")
            
            # Jobs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT UNIQUE,
                source TEXT,
                description TEXT,
                requirements TEXT,
                salary TEXT,
                company_rating TEXT,
                posted_date TEXT,
                status TEXT DEFAULT 'new',
                match_score REAL DEFAULT 0,
                is_live INTEGER DEFAULT 1,
                scrape_mode TEXT DEFAULT 'live',
                scraped_at TEXT,
                user_id TEXT,
                created_at TEXT
            );
            """)
            self._ensure_column(cursor, "jobs", "is_live", "INTEGER DEFAULT 1")
            self._ensure_column(cursor, "jobs", "scrape_mode", "TEXT DEFAULT 'live'")
            self._ensure_column(cursor, "jobs", "scraped_at", "TEXT")
            
            # Contacts
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                company TEXT,
                role TEXT,
                linkedin_url TEXT,
                source TEXT,
                notes TEXT,
                sent_emails INTEGER DEFAULT 0,
                last_contact TEXT,
                user_id TEXT,
                created_at TEXT
            );
            """)
            
            # Applications
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                applied_date TEXT,
                status TEXT DEFAULT 'applied',
                follow_up_date TEXT,
                notes TEXT,
                user_id TEXT,
                created_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL
            );
            """)
            
            # Emails
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                subject TEXT,
                body TEXT,
                template_used TEXT,
                sent_date TEXT,
                status TEXT DEFAULT 'sent',
                user_id TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE SET NULL
            );
            """)
            
            # Metrics
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                jobs_viewed INTEGER DEFAULT 0,
                jobs_saved INTEGER DEFAULT 0,
                applications_sent INTEGER DEFAULT 0,
                responses_received INTEGER DEFAULT 0,
                interviews_scheduled INTEGER DEFAULT 0,
                user_id TEXT
            );
            """)
            
            # Documents
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL, -- 'cv', 'certificate', 'cover_letter', 'other'
                file_path TEXT NOT NULL,
                file_url TEXT,
                file_size INTEGER,
                uploaded_at TEXT NOT NULL
            );
            """)
            self._ensure_column(cursor, "documents", "file_url", "TEXT")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_credentials (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            conn.commit()
            logger.info("SQLite tables verified / initialized.")

    def _ensure_column(self, cursor: sqlite3.Cursor, table: str, column: str, definition: str):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cursor.fetchall()}
        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def get_auth_credentials(self) -> Optional[Dict[str, Any]]:
        """Return dynamic auth credentials if the password was changed in-app."""
        if self.uses_supabase_primary:
            try:
                result = (
                    self._supabase_required()
                    .table("auth_credentials")
                    .select("*")
                    .eq("id", "primary")
                    .limit(1)
                    .execute()
                )
                data = result.data or []
                return data[0] if data else None
            except Exception as e:
                logger.warning(f"Failed to read dynamic auth credentials from Supabase: {e}")
                return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM auth_credentials WHERE id = ?", ("primary",))
            row = cursor.fetchone()
            return dict(row) if row else None

    def set_auth_credentials(self, username: str, password_hash: str, password_salt: str) -> Dict[str, Any]:
        """Persist a hashed login password without requiring hosting env changes."""
        now = datetime.now().isoformat()
        payload = {
            "id": "primary",
            "username": username,
            "password_hash": password_hash,
            "password_salt": password_salt,
            "updated_at": now,
        }

        if self.uses_supabase_primary:
            result = self._supabase_required().table("auth_credentials").upsert(payload).execute()
            data = result.data or []
            return data[0] if data else payload

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO auth_credentials (id, username, password_hash, password_salt, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username=excluded.username,
                    password_hash=excluded.password_hash,
                    password_salt=excluded.password_salt,
                    updated_at=excluded.updated_at
                """,
                ("primary", username, password_hash, password_salt, now),
            )
            conn.commit()
        return payload

    def seed_mock_data_if_empty(self):
        """Seed mock data into database if empty, to ensure app looks alive immediately"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check jobs
            cursor.execute("SELECT count(*) FROM jobs")
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding initial mock jobs...")
                sample_jobs = [
                    ("Senior Python Developer", "TechCorp", "Remote", "https://techcorp.com/jobs/1", "linkedin", "We are looking for a Senior Python Developer with FastAPI and SQLite experience.", "Python, SQLite, FastAPI", "$120,000 - $140,000", "4.2", "2026-05-18", "new", 95.0, 0, "demo", datetime.now().isoformat(), None, datetime.now().isoformat()),
                    ("Full Stack Engineer", "WebLabs LLC", "New York, NY", "https://weblabs.io/careers/react-python", "remotive", "React and Python developer needed to build modern SaaS platforms.", "React, Python, TailwindCSS", "$90,000 - $110,000", "3.9", "2026-05-19", "new", 80.0, 0, "demo", datetime.now().isoformat(), None, datetime.now().isoformat()),
                    ("DevOps Engineer", "CloudSystems", "Remote", "https://cloudsystems.com/devops", "weworkremotely", "Manage AWS infrastructure and CI/CD pipelines.", "AWS, Docker, CI/CD", "$130,000 - $150,000", "4.5", "2026-05-20", "applied", 70.0, 0, "demo", datetime.now().isoformat(), None, datetime.now().isoformat()),
                ]
                cursor.executemany("""
                INSERT OR IGNORE INTO jobs (title, company, location, url, source, description, requirements, salary, company_rating, posted_date, status, match_score, is_live, scrape_mode, scraped_at, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sample_jobs)
            
            # Check profile
            cursor.execute("SELECT count(*) FROM user_profiles")
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding initial user profile...")
                skills = json.dumps(["Python", "JavaScript", "React", "FastAPI", "SQLite", "Git"])
                social_links = json.dumps([
                    {"label": "Calendly", "url": "https://calendly.com/example"},
                    {"label": "Blog", "url": "https://example.com/blog"},
                ])
                cursor.execute("""
                INSERT INTO user_profiles (id, full_name, email, phone, location, headline, bio, cv_url, portfolio_url, github_url, linkedin_url, social_links, skills, experience, education, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("default", "Demo Candidate", "candidate@example.com", "+1 555 0100", "Remote", "Full Stack Python Developer", "Demo profile used to calibrate matching against backend and frontend roles.", "", "https://example.com/portfolio", "https://github.com/example", "https://linkedin.com/in/example", social_links, skills, "Senior", "Computer Science", datetime.now().isoformat(), datetime.now().isoformat()))

            # Check contacts
            cursor.execute("SELECT count(*) FROM contacts")
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding initial contacts...")
                sample_contacts = [
                    ("Sarah Johnson", "sarah.j@techcorp.com", "TechCorp", "Senior Recruiter", "https://linkedin.com/in/sarahjohnson", "linkedin", "Contacted about Full Stack role", 1, "2026-05-19", None, datetime.now().isoformat()),
                    ("Mike Chen", "mike.c@weblabs.io", "WebLabs LLC", "Engineering Manager", "https://linkedin.com/in/mikechen", "manual", "Emailed directly", 0, None, None, datetime.now().isoformat())
                ]
                cursor.executemany("""
                INSERT OR IGNORE INTO contacts (name, email, company, role, linkedin_url, source, notes, sent_emails, last_contact, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sample_contacts)

            # Check applications
            cursor.execute("SELECT count(*) FROM applications")
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding initial applications...")
                sample_apps = [
                    (1, "TechCorp", "Senior Python Developer", "2026-05-19", "applied", "2026-05-26", "Awaiting recruiter response", None, datetime.now().isoformat())
                ]
                cursor.executemany("""
                INSERT OR IGNORE INTO applications (job_id, company, position, applied_date, status, follow_up_date, notes, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sample_apps)
                
            conn.commit()

    # ==================== SYNC HELPER ====================
    def _sync_to_supabase(self, table: str, data: Dict[str, Any]):
        """Helper to sync write operations to Supabase in a non-blocking way"""
        if not self.supabase_client or self.uses_supabase_primary:
            return
        
        try:
            # RLS policy handles authentication check
            self.supabase_client.table(table).upsert(data).execute()
            logger.info(f"Successfully synced data to Supabase table: {table}")
        except Exception as e:
            logger.warning(f"Failed to sync to Supabase table {table}: {e} (App will continue running locally)")

    # ==================== PROFILE METHODS ====================
    def get_profile(self) -> Dict[str, Any]:
        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table("user_profiles").select("*").eq("id", "default").limit(1).execute()
                if result.data:
                    return self._normalize_record(result.data[0])
            except Exception as e:
                logger.warning(f"Failed to read profile from Supabase: {e}")
            return {}

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE id = 'default'")
            row = cursor.fetchone()
            if row:
                profile = dict(row)
                # Decode skills JSON
                try:
                    profile['skills'] = json.loads(profile['skills']) if profile.get('skills') else []
                except Exception:
                    profile['skills'] = []
                try:
                    profile['social_links'] = json.loads(profile['social_links']) if profile.get('social_links') else []
                except Exception:
                    profile['social_links'] = []
                return profile
            return {}

    def save_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_profile()
        merged = {**existing, **profile_data}
        skills_json = json.dumps(merged.get('skills', []))
        social_links_json = json.dumps(merged.get('social_links', []))
        
        # Prepare fields
        full_name = merged.get('full_name')
        email = merged.get('email')
        phone = merged.get('phone')
        location = merged.get('location')
        headline = merged.get('headline')
        bio = merged.get('bio')
        cv_url = merged.get('cv_url')
        portfolio_url = merged.get('portfolio_url')
        github_url = merged.get('github_url')
        linkedin_url = merged.get('linkedin_url')
        experience = merged.get('experience')
        education = merged.get('education')
        now = datetime.now().isoformat()

        if self.uses_supabase_primary:
            sync_data = {
                'id': 'default', 'full_name': full_name, 'email': email, 'phone': phone,
                'location': location, 'headline': headline, 'bio': bio, 'cv_url': cv_url,
                'portfolio_url': portfolio_url, 'github_url': github_url, 'linkedin_url': linkedin_url,
                'social_links': merged.get('social_links', []), 'skills': merged.get('skills', []),
                'experience': experience, 'education': education,
                'updated_at': now
            }
            try:
                self._supabase_required().table('user_profiles').upsert(sync_data, on_conflict='id').execute()
            except TypeError:
                self._supabase_required().table('user_profiles').upsert(sync_data).execute()
            return self.get_profile()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO user_profiles (id, full_name, email, phone, location, headline, bio, cv_url, portfolio_url, github_url, linkedin_url, social_links, skills, experience, education, created_at, updated_at)
            VALUES ('default', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                full_name=excluded.full_name,
                email=excluded.email,
                phone=excluded.phone,
                location=excluded.location,
                headline=excluded.headline,
                bio=excluded.bio,
                cv_url=excluded.cv_url,
                portfolio_url=excluded.portfolio_url,
                github_url=excluded.github_url,
                linkedin_url=excluded.linkedin_url,
                social_links=excluded.social_links,
                skills=excluded.skills,
                experience=excluded.experience,
                education=excluded.education,
                updated_at=excluded.updated_at
            """, (full_name, email, phone, location, headline, bio, cv_url, portfolio_url, github_url, linkedin_url, social_links_json, skills_json, experience, education, now, now))
            conn.commit()
            
        # Try syncing
        sync_data = {
            'id': 'default', 'full_name': full_name, 'email': email, 'phone': phone,
            'location': location, 'headline': headline, 'bio': bio, 'cv_url': cv_url,
            'portfolio_url': portfolio_url, 'github_url': github_url, 'linkedin_url': linkedin_url,
            'social_links': merged.get('social_links', []), 'skills': merged.get('skills', []),
            'experience': experience, 'education': education,
            'updated_at': now
        }
        self._sync_to_supabase('user_profiles', sync_data)
        
        return self.get_profile()

    # ==================== JOBS METHODS ====================
    def get_jobs(self, source: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if self.uses_supabase_primary:
            try:
                query = self._supabase_required().table("jobs").select("*")
                if source:
                    query = query.eq("source", source)
                if status:
                    query = query.eq("status", status)
                result = query.order("id", desc=True).limit(limit).execute()
                return [self._normalize_record(row) for row in (result.data or [])]
            except Exception as e:
                logger.warning(f"Failed to read jobs from Supabase: {e}")
                return []

        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        
        if source:
            query += " AND source = ?"
            params.append(source)
        if status:
            query += " AND status = ?"
            params.append(status)
            
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_job_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table("jobs").select("*").eq("url", url).limit(1).execute()
                return self._normalize_record(result.data[0]) if result.data else None
            except Exception as e:
                logger.warning(f"Failed to read job by URL from Supabase: {e}")
                return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE url = ?", (url,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        title = job_data.get('title')
        company = job_data.get('company')
        location = job_data.get('location')
        url = job_data.get('url')
        source = job_data.get('source', 'manual')
        description = job_data.get('description', '')
        requirements = job_data.get('requirements', '')
        salary = job_data.get('salary')
        company_rating = job_data.get('company_rating')
        posted_date = job_data.get('posted_date')
        status = job_data.get('status', 'new')
        match_score = job_data.get('match_score', 0.0)
        is_live = 1 if job_data.get('is_live', True) else 0
        scrape_mode = job_data.get('scrape_mode') or ("live" if is_live else "demo")
        scraped_at = job_data.get('scraped_at')
        user_id = job_data.get('user_id')
        now = datetime.now().isoformat()

        new_job = {
            'title': title, 'company': company, 'location': location, 'url': url,
            'source': source, 'description': description, 'requirements': requirements, 'salary': salary,
            'company_rating': company_rating, 'posted_date': posted_date, 'status': status, 'match_score': match_score,
            'is_live': bool(is_live), 'scrape_mode': scrape_mode, 'scraped_at': scraped_at,
            'user_id': user_id, 'created_at': now
        }

        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table('jobs').upsert(new_job, on_conflict='url').execute()
            except TypeError:
                result = self._supabase_required().table('jobs').upsert(new_job).execute()
            saved = result.data[0] if result.data else new_job
            return self._normalize_record(saved)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO jobs (title, company, location, url, source, description, requirements, salary, company_rating, posted_date, status, match_score, is_live, scrape_mode, scraped_at, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, company, location, url, source, description, requirements, salary, company_rating, posted_date, status, match_score, is_live, scrape_mode, scraped_at, user_id, now))
                conn.commit()
                job_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # If unique constraint on URL fails, update match score or existing job status
                cursor.execute("SELECT id FROM jobs WHERE url = ?", (url,))
                job_id = cursor.fetchone()[0]
                cursor.execute("""
                UPDATE jobs SET title=?, company=?, location=?, source=?, description=?, requirements=?, salary=?, company_rating=?, posted_date=?, match_score=?, is_live=?, scrape_mode=?, scraped_at=?
                WHERE id = ?
                """, (title, company, location, source, description, requirements, salary, company_rating, posted_date, match_score, is_live, scrape_mode, scraped_at, job_id))
                conn.commit()
                
        new_job = {
            'id': job_id, 'title': title, 'company': company, 'location': location, 'url': url,
            'source': source, 'description': description, 'requirements': requirements, 'salary': salary,
            'company_rating': company_rating, 'posted_date': posted_date, 'status': status, 'match_score': match_score,
            'is_live': bool(is_live), 'scrape_mode': scrape_mode, 'scraped_at': scraped_at,
            'user_id': user_id, 'created_at': now
        }
        
        # Try syncing to Supabase
        self._sync_to_supabase('jobs', new_job)
        
        return new_job

    def update_job(self, job_id: int, status: Optional[str] = None, match_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if self.uses_supabase_primary:
            updates = {}
            if status is not None:
                updates["status"] = status
            if match_score is not None:
                updates["match_score"] = match_score
            if not updates:
                return None
            try:
                result = self._supabase_required().table("jobs").update(updates).eq("id", job_id).execute()
                return self._normalize_record(result.data[0]) if result.data else None
            except Exception as e:
                logger.warning(f"Failed to update job in Supabase: {e}")
                return None

        if status is None and match_score is None:
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status is not None:
                cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
            if match_score is not None:
                cursor.execute("UPDATE jobs SET match_score = ? WHERE id = ?", (match_score, job_id))
            conn.commit()
            
            # Retrieve updated job
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                job_dict = dict(row)
                self._sync_to_supabase('jobs', job_dict)
                return job_dict
        return None

    def delete_job(self, job_id: int) -> bool:
        if self.uses_supabase_primary:
            try:
                self._supabase_required().table('jobs').delete().eq('id', job_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete job {job_id} from Supabase: {e}")
                return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            
        # Try syncing deletions by deleting from Supabase
        if self.supabase_client:
            try:
                self.supabase_client.table('jobs').delete().eq('id', job_id).execute()
            except Exception as e:
                logger.warning(f"Failed to delete job {job_id} from Supabase: {e}")
        return True

    # ==================== CONTACTS METHODS ====================
    def get_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table("contacts").select("*").order("id", desc=True).limit(limit).execute()
                return [self._normalize_record(row) for row in (result.data or [])]
            except Exception as e:
                logger.warning(f"Failed to read contacts from Supabase: {e}")
                return []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def add_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        name = contact_data.get('name')
        email = contact_data.get('email')
        company = contact_data.get('company')
        role = contact_data.get('role')
        linkedin_url = contact_data.get('linkedin_url')
        source = contact_data.get('source', 'manual')
        notes = contact_data.get('notes', '')
        sent_emails = contact_data.get('sent_emails', 0)
        last_contact = contact_data.get('last_contact')
        user_id = contact_data.get('user_id')
        now = datetime.now().isoformat()

        new_contact = {
            'name': name, 'email': email, 'company': company, 'role': role,
            'linkedin_url': linkedin_url, 'source': source, 'notes': notes, 'sent_emails': sent_emails,
            'last_contact': last_contact, 'user_id': user_id, 'created_at': now
        }

        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table('contacts').upsert(new_contact, on_conflict='email').execute()
            except TypeError:
                result = self._supabase_required().table('contacts').upsert(new_contact).execute()
            saved = result.data[0] if result.data else new_contact
            return self._normalize_record(saved)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO contacts (name, email, company, role, linkedin_url, source, notes, sent_emails, last_contact, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, email, company, role, linkedin_url, source, notes, sent_emails, last_contact, user_id, now))
                conn.commit()
                contact_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # If unique constraint on email fails, update contact info instead
                cursor.execute("SELECT id FROM contacts WHERE email = ?", (email,))
                contact_id = cursor.fetchone()[0]
                cursor.execute("""
                UPDATE contacts SET name=?, company=?, role=?, linkedin_url=?, source=?, notes=?
                WHERE id = ?
                """, (name, company, role, linkedin_url, source, notes, contact_id))
                conn.commit()
                
        new_contact = {
            'id': contact_id, 'name': name, 'email': email, 'company': company, 'role': role,
            'linkedin_url': linkedin_url, 'source': source, 'notes': notes, 'sent_emails': sent_emails,
            'last_contact': last_contact, 'user_id': user_id, 'created_at': now
        }
        self._sync_to_supabase('contacts', new_contact)
        return new_contact

    def increment_sent_emails(self, email: str):
        if self.uses_supabase_primary:
            today = datetime.now().strftime("%Y-%m-%d")
            try:
                result = self._supabase_required().table("contacts").select("id,sent_emails").eq("email", email).limit(1).execute()
                if result.data:
                    row = result.data[0]
                    self._supabase_required().table("contacts").update({
                        "sent_emails": int(row.get("sent_emails") or 0) + 1,
                        "last_contact": today,
                    }).eq("id", row["id"]).execute()
            except Exception as e:
                logger.warning(f"Failed to increment sent email count in Supabase: {e}")
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("UPDATE contacts SET sent_emails = sent_emails + 1, last_contact = ? WHERE email = ?", (today, email))
            conn.commit()

    def delete_contact(self, contact_id: int) -> bool:
        """Deletes a contact and its email history."""
        if self.uses_supabase_primary:
            try:
                existing = self._supabase_required().table("contacts").select("id").eq("id", contact_id).limit(1).execute()
                if not existing.data:
                    return False
                self._supabase_required().table("emails").delete().eq("contact_id", contact_id).execute()
                self._supabase_required().table("contacts").delete().eq("id", contact_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete contact {contact_id} from Supabase: {e}")
                return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("DELETE FROM emails WHERE contact_id = ?", (contact_id,))
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            conn.commit()
        return True

    # ==================== APPLICATIONS METHODS ====================
    def get_applications(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.uses_supabase_primary:
            try:
                query = self._supabase_required().table("applications").select("*")
                if status:
                    query = query.eq("status", status)
                result = query.order("id", desc=True).execute()
                return [self._normalize_record(row) for row in (result.data or [])]
            except Exception as e:
                logger.warning(f"Failed to read applications from Supabase: {e}")
                return []

        query = "SELECT * FROM applications WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id DESC"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def add_application(self, app_data: Dict[str, Any]) -> Dict[str, Any]:
        job_id = app_data.get('job_id')
        company = app_data.get('company')
        position = app_data.get('position')
        applied_date = app_data.get('applied_date') or datetime.now().strftime("%Y-%m-%d")
        status = app_data.get('status', 'applied')
        follow_up_date = app_data.get('follow_up_date')
        notes = app_data.get('notes')
        user_id = app_data.get('user_id')
        now = datetime.now().isoformat()

        new_app = {
            'job_id': job_id, 'company': company, 'position': position,
            'applied_date': applied_date, 'status': status, 'follow_up_date': follow_up_date,
            'notes': notes, 'user_id': user_id, 'created_at': now
        }

        if self.uses_supabase_primary:
            result = self._supabase_required().table('applications').insert(new_app).execute()
            saved = result.data[0] if result.data else new_app
            return self._normalize_record(saved)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO applications (job_id, company, position, applied_date, status, follow_up_date, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, company, position, applied_date, status, follow_up_date, notes, user_id, now))
            conn.commit()
            app_id = cursor.lastrowid
            
        new_app = {
            'id': app_id, 'job_id': job_id, 'company': company, 'position': position,
            'applied_date': applied_date, 'status': status, 'follow_up_date': follow_up_date,
            'notes': notes, 'user_id': user_id, 'created_at': now
        }
        self._sync_to_supabase('applications', new_app)
        return new_app

    def get_application(self, app_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single application by ID"""
        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table("applications").select("*").eq("id", app_id).limit(1).execute()
                return self._normalize_record(result.data[0]) if result.data else None
            except Exception as e:
                logger.warning(f"Failed to read application from Supabase: {e}")
                return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_application(self, app_id: int, status: Optional[str] = None, follow_up_date: Optional[str] = None, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Updates application state in SQLite"""
        if self.uses_supabase_primary:
            updates = {}
            if status is not None:
                updates["status"] = status
            if follow_up_date is not None:
                updates["follow_up_date"] = follow_up_date
            if notes is not None:
                updates["notes"] = notes
            if not updates:
                return self.get_application(app_id)
            result = self._supabase_required().table("applications").update(updates).eq("id", app_id).execute()
            return self._normalize_record(result.data[0]) if result.data else None

        if status is None and follow_up_date is None and notes is None:
            return self.get_application(app_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status is not None:
                cursor.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
            if follow_up_date is not None:
                cursor.execute("UPDATE applications SET follow_up_date = ? WHERE id = ?", (follow_up_date, app_id))
            if notes is not None:
                cursor.execute("UPDATE applications SET notes = ? WHERE id = ?", (notes, app_id))
            conn.commit()
            
        return self.get_application(app_id)

    def delete_application(self, app_id: int) -> bool:
        """Deletes an application from SQLite"""
        if self.uses_supabase_primary:
            try:
                self._supabase_required().table("applications").delete().eq("id", app_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete application from Supabase: {e}")
                return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== METRICS METHODS ====================
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates aggregated metrics directly from SQLite database"""
        if self.uses_supabase_primary:
            jobs = self.get_jobs(limit=1000)
            applications = self.get_applications()
            contacts = self.get_contacts(limit=1000)
            stats = {
                "jobs": {"total": len(jobs), "by_status": {}, "by_source": {}},
                "applications": {"total": len(applications), "by_status": {}, "recent_week": 0},
                "contacts": {"total": len(contacts)},
                "system": "supabase"
            }
            for job in jobs:
                status = job.get("status") or "unknown"
                source = job.get("source") or "unknown"
                stats["jobs"]["by_status"][status] = stats["jobs"]["by_status"].get(status, 0) + 1
                stats["jobs"]["by_source"][source] = stats["jobs"]["by_source"].get(source, 0) + 1
            for app in applications:
                status = app.get("status") or "unknown"
                stats["applications"]["by_status"][status] = stats["applications"]["by_status"].get(status, 0) + 1
            return stats

        stats = {
            "jobs": {"total": 0, "by_status": {}, "by_source": {}},
            "applications": {"total": 0, "by_status": {}, "recent_week": 0},
            "contacts": {"total": 0},
            "system": "sqlite_hybrid"
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count jobs
            cursor.execute("SELECT count(*), status, source FROM jobs GROUP BY status, source")
            rows = cursor.fetchall()
            for row in rows:
                count, status, source = row
                stats["jobs"]["total"] += count
                stats["jobs"]["by_status"][status] = stats["jobs"]["by_status"].get(status, 0) + count
                stats["jobs"]["by_source"][source] = stats["jobs"]["by_source"].get(source, 0) + count
                
            # Count apps
            cursor.execute("SELECT count(*), status FROM applications GROUP BY status")
            rows = cursor.fetchall()
            for row in rows:
                count, status = row
                stats["applications"]["total"] += count
                stats["applications"]["by_status"][status] = stats["applications"]["by_status"].get(status, 0) + count
            
            # Count contacts
            cursor.execute("SELECT count(*) FROM contacts")
            stats["contacts"]["total"] = cursor.fetchone()[0]
            
        return stats

    # ==================== DOCUMENTS METHODS ====================
    def add_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves document metadata to SQLite"""
        now = datetime.now().isoformat()
        if self.uses_supabase_primary:
            payload = {
                "name": doc_data.get("name"),
                "filename": doc_data.get("filename"),
                "file_type": doc_data.get("file_type", "other"),
                "file_path": doc_data.get("file_path"),
                "file_url": doc_data.get("file_url"),
                "file_size": doc_data.get("file_size"),
                "uploaded_at": now,
            }
            result = self._supabase_required().table("documents").insert(payload).execute()
            return self._normalize_record(result.data[0] if result.data else payload)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO documents (name, filename, file_type, file_path, file_url, file_size, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_data.get("name"),
                doc_data.get("filename"),
                doc_data.get("file_type", "other"),
                doc_data.get("file_path"),
                doc_data.get("file_url"),
                doc_data.get("file_size"),
                now
            ))
            conn.commit()
            doc_id = cursor.lastrowid
            
        return {
            "id": doc_id,
            "name": doc_data.get("name"),
            "filename": doc_data.get("filename"),
            "file_type": doc_data.get("file_type", "other"),
            "file_path": doc_data.get("file_path"),
            "file_url": doc_data.get("file_url"),
            "file_size": doc_data.get("file_size"),
            "uploaded_at": now
        }

    def get_documents(self) -> List[Dict[str, Any]]:
        """Retrieves all documents metadata from SQLite"""
        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table("documents").select("*").order("uploaded_at", desc=True).execute()
                return [self._normalize_record(row) for row in (result.data or [])]
            except Exception as e:
                logger.warning(f"Failed to read documents from Supabase: {e}")
                return []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single document's metadata from SQLite"""
        if self.uses_supabase_primary:
            try:
                result = self._supabase_required().table("documents").select("*").eq("id", doc_id).limit(1).execute()
                return self._normalize_record(result.data[0]) if result.data else None
            except Exception as e:
                logger.warning(f"Failed to read document from Supabase: {e}")
                return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_document(self, doc_id: int) -> bool:
        """Deletes document metadata from SQLite"""
        if self.uses_supabase_primary:
            try:
                self._supabase_required().table("documents").delete().eq("id", doc_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete document from Supabase: {e}")
                return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== EMAIL METHODS ====================
    def add_email_log(self, contact_email: str, subject: str, body: str, status: str = "sent") -> Dict[str, Any]:
        if self.uses_supabase_primary:
            contact_id = None
            try:
                contact = self._supabase_required().table("contacts").select("id").eq("email", contact_email).limit(1).execute()
                if contact.data:
                    contact_id = contact.data[0].get("id")
                payload = {
                    "contact_id": contact_id,
                    "subject": subject,
                    "body": body,
                    "status": status,
                    "sent_date": datetime.now().isoformat(),
                }
                result = self._supabase_required().table("emails").insert(payload).execute()
                return self._normalize_record(result.data[0] if result.data else payload)
            except Exception as e:
                logger.warning(f"Failed to log email in Supabase: {e}")
                return {}

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM contacts WHERE email = ?", (contact_email,))
            row = cursor.fetchone()
            contact_id = row[0] if row else None
            cursor.execute("""
            INSERT INTO emails (contact_id, subject, body, sent_date, status)
            VALUES (?, ?, ?, datetime('now'), ?)
            """, (contact_id, subject, body, status))
            conn.commit()
            return {
                "id": cursor.lastrowid,
                "contact_id": contact_id,
                "subject": subject,
                "body": body,
                "status": status,
            }

    def get_emails(self, contact_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if self.uses_supabase_primary:
            try:
                query = self._supabase_required().table("emails").select("*")
                if contact_id:
                    query = query.eq("contact_id", contact_id)
                result = query.order("sent_date", desc=True).execute()
                return [self._normalize_record(row) for row in (result.data or [])]
            except Exception as e:
                logger.warning(f"Failed to read emails from Supabase: {e}")
                return []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if contact_id:
                cursor.execute("SELECT * FROM emails WHERE contact_id = ? ORDER BY sent_date DESC", (contact_id,))
            else:
                cursor.execute("SELECT * FROM emails ORDER BY sent_date DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
