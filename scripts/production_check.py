#!/usr/bin/env python3
"""Validate production environment variables before deploying JobHunter Pro."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Mapping


REQUIRED_PRODUCTION_VALUES = (
    "AUTH_ENABLED",
    "AUTH_PASSWORD",
    "AUTH_SECRET_KEY",
    "AUTH_COOKIE_SECURE",
    "CORS_ALLOWED_ORIGINS",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_STORAGE_BUCKET",
)

PLACEHOLDER_MARKERS = (
    "replace-with",
    "your-",
    "example.com",
    "example.supabase.co",
)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def validate_environment(env: Mapping[str, str]) -> list[str]:
    issues: list[str] = []
    if str(env.get("APP_ENV", "")).strip().lower() != "production":
        issues.append("APP_ENV must be production.")

    for key in REQUIRED_PRODUCTION_VALUES:
        if not str(env.get(key, "")).strip():
            issues.append(f"Missing {key}.")
        elif any(marker in str(env.get(key, "")).strip().lower() for marker in PLACEHOLDER_MARKERS):
            issues.append(f"{key} still contains a placeholder value.")

    if str(env.get("AUTH_ENABLED", "")).strip().lower() != "true":
        issues.append("AUTH_ENABLED must be true.")
    if str(env.get("AUTH_COOKIE_SECURE", "")).strip().lower() != "true":
        issues.append("AUTH_COOKIE_SECURE must be true.")
    if _bool(env.get("AUTH_RETURN_BEARER_TOKEN")):
        issues.append("AUTH_RETURN_BEARER_TOKEN must be false.")
    if str(env.get("DEMO_MODE", "")).strip().lower() != "false":
        issues.append("DEMO_MODE must be false for real vacancies.")
    if str(env.get("SCRAPER_ALLOW_FALLBACKS", "")).strip().lower() != "false":
        issues.append("SCRAPER_ALLOW_FALLBACKS must be false for real vacancies.")

    origins = [origin.strip() for origin in str(env.get("CORS_ALLOWED_ORIGINS", "")).split(",") if origin.strip()]
    if not origins:
        issues.append("CORS_ALLOWED_ORIGINS must include your deployed origin.")
    if "*" in origins:
        issues.append("CORS_ALLOWED_ORIGINS must not include wildcard origins.")
    if "null" in origins:
        issues.append("CORS_ALLOWED_ORIGINS must not include null.")
    if any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
        issues.append("CORS_ALLOWED_ORIGINS must not include localhost origins.")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JobHunter Pro production env configuration.")
    parser.add_argument("--env-file", type=Path, help="Path to a .env-style file to validate.")
    args = parser.parse_args()

    env = dict(os.environ)
    if args.env_file:
        env.update(parse_env_file(args.env_file))

    issues = validate_environment(env)
    if issues:
        print("Production configuration is not ready:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Production configuration looks ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
