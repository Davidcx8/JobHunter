"""
Centralized runtime settings for JobHunter Pro.

Sensitive values must come from local environment files or process
environment variables. This module intentionally does not provide secret
fallbacks.
"""

from dataclasses import dataclass
from pathlib import Path
import os
import secrets

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Local-only files. They are ignored by git and optional in production.
load_dotenv(BASE_DIR / "config.env")
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local")


def _csv(value: str, default: list[str]) -> list[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = _int(os.getenv("API_PORT"), 8000)
    api_debug: bool = _bool(os.getenv("API_DEBUG"), False)
    demo_mode: bool = _bool(os.getenv("DEMO_MODE"), True)
    scraper_allow_fallbacks: bool = _bool(os.getenv("SCRAPER_ALLOW_FALLBACKS"), True)
    auth_enabled: bool = _bool(os.getenv("AUTH_ENABLED"), False)
    auth_username: str = os.getenv("AUTH_USERNAME", "admin")
    auth_password: str = os.getenv("AUTH_PASSWORD", "")
    auth_secret_key: str = os.getenv("AUTH_SECRET_KEY", "")
    auth_token_ttl_minutes: int = _int(os.getenv("AUTH_TOKEN_TTL_MINUTES"), 720)
    auth_cookie_secure: bool = _bool(os.getenv("AUTH_COOKIE_SECURE"), False)
    storage_backend: str = os.getenv("STORAGE_BACKEND", "sqlite").strip().lower()
    db_path: str = os.getenv("DB_PATH", "./data/jobhunter.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    max_upload_mb: int = _int(os.getenv("MAX_UPLOAD_MB"), 10)
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "")
    cors_allowed_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "null",
        ]
        object.__setattr__(
            self,
            "cors_allowed_origins",
            _csv(os.getenv("CORS_ALLOWED_ORIGINS", ""), default_origins),
        )

    @property
    def resolved_db_path(self) -> Path:
        path = Path(self.db_path)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def resolved_upload_dir(self) -> Path:
        path = Path(self.upload_dir)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def auth_configured(self) -> bool:
        return bool(self.auth_password and self.auth_secret_key)

    @property
    def resolved_auth_secret(self) -> str:
        if self.auth_secret_key:
            return self.auth_secret_key
        # Runtime-only fallback for local experiments when auth is disabled.
        return secrets.token_urlsafe(32)


settings = Settings()
