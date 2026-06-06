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


def _has_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return any(marker in lowered for marker in ("replace-with", "your-", "example.com", "example.supabase.co"))


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
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
    auth_return_bearer_token: bool = _bool(os.getenv("AUTH_RETURN_BEARER_TOKEN"), False)
    auth_login_max_failures: int = _int(os.getenv("AUTH_LOGIN_MAX_FAILURES"), 5)
    auth_login_lockout_seconds: int = _int(os.getenv("AUTH_LOGIN_LOCKOUT_SECONDS"), 300)
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
    def is_production(self) -> bool:
        return self.app_env in {"prod", "production"}

    @property
    def resolved_auth_secret(self) -> str:
        if self.auth_secret_key:
            return self.auth_secret_key
        # Runtime-only fallback for local experiments when auth is disabled.
        return secrets.token_urlsafe(32)

    def validate_runtime_configuration(self) -> list[str]:
        issues: list[str] = []
        if self.auth_enabled and not self.auth_configured:
            issues.append("AUTH_PASSWORD and AUTH_SECRET_KEY are required when AUTH_ENABLED is true.")
        if self.auth_login_max_failures < 1:
            issues.append("AUTH_LOGIN_MAX_FAILURES must be at least 1.")
        if self.auth_login_lockout_seconds < 1:
            issues.append("AUTH_LOGIN_LOCKOUT_SECONDS must be at least 1.")
        if not self.is_production:
            return issues

        if not self.auth_enabled:
            issues.append("AUTH_ENABLED must be true in production.")
        if not self.auth_configured:
            issues.append("AUTH_PASSWORD and AUTH_SECRET_KEY are required in production.")
        if not self.auth_cookie_secure:
            issues.append("AUTH_COOKIE_SECURE must be true in production.")
        if self.auth_return_bearer_token:
            issues.append("AUTH_RETURN_BEARER_TOKEN must be false in production.")
        if "*" in self.cors_allowed_origins:
            issues.append("CORS_ALLOWED_ORIGINS must not include wildcard origins in production.")
        if "null" in self.cors_allowed_origins:
            issues.append("CORS_ALLOWED_ORIGINS must not include null in production.")
        if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_allowed_origins):
            issues.append("CORS_ALLOWED_ORIGINS must not include localhost origins in production.")
        if self.storage_backend == "supabase" and not os.getenv("SUPABASE_SERVICE_KEY"):
            issues.append("SUPABASE_SERVICE_KEY is required when STORAGE_BACKEND=supabase in production.")
        if _has_placeholder(self.auth_password):
            issues.append("AUTH_PASSWORD must not use a placeholder value in production.")
        if _has_placeholder(self.auth_secret_key):
            issues.append("AUTH_SECRET_KEY must not use a placeholder value in production.")
        if _has_placeholder(os.getenv("SUPABASE_SERVICE_KEY", "")):
            issues.append("SUPABASE_SERVICE_KEY must not use a placeholder value in production.")
        if any(_has_placeholder(origin) for origin in self.cors_allowed_origins):
            issues.append("CORS_ALLOWED_ORIGINS must not use placeholder origins in production.")
        return issues

    def require_valid_runtime_configuration(self) -> None:
        issues = self.validate_runtime_configuration()
        if issues:
            raise RuntimeError("Invalid JobHunter Pro configuration: " + " ".join(issues))


settings = Settings()
