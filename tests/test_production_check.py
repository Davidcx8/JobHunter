from scripts.production_check import validate_environment


def test_validate_environment_reports_missing_required_values():
    issues = validate_environment({"APP_ENV": "production"})

    assert "Missing AUTH_ENABLED." in issues
    assert "Missing AUTH_PASSWORD." in issues
    assert "Missing SUPABASE_SERVICE_KEY." in issues


def test_validate_environment_accepts_secure_production_values():
    issues = validate_environment({
        "APP_ENV": "production",
        "AUTH_ENABLED": "true",
        "AUTH_PASSWORD": "long-password",
        "AUTH_SECRET_KEY": "long-secret",
        "AUTH_COOKIE_SECURE": "true",
        "AUTH_RETURN_BEARER_TOKEN": "false",
        "CORS_ALLOWED_ORIGINS": "https://jobhunter.davidcx8.dev",
        "STORAGE_BACKEND": "supabase",
        "SUPABASE_URL": "https://abc123.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_KEY": "service",
        "SUPABASE_STORAGE_BUCKET": "jobhunter-documents",
        "DEMO_MODE": "false",
        "SCRAPER_ALLOW_FALLBACKS": "false",
    })

    assert issues == []


def test_validate_environment_rejects_placeholder_values():
    issues = validate_environment({
        "APP_ENV": "production",
        "AUTH_ENABLED": "true",
        "AUTH_PASSWORD": "replace-with-a-long-random-password",
        "AUTH_SECRET_KEY": "replace-with-a-long-random-secret",
        "AUTH_COOKIE_SECURE": "true",
        "AUTH_RETURN_BEARER_TOKEN": "false",
        "CORS_ALLOWED_ORIGINS": "https://your-domain.example",
        "STORAGE_BACKEND": "supabase",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_ANON_KEY": "replace-with-anon-key",
        "SUPABASE_SERVICE_KEY": "replace-with-service-role-key",
        "SUPABASE_STORAGE_BUCKET": "jobhunter-documents",
        "DEMO_MODE": "false",
        "SCRAPER_ALLOW_FALLBACKS": "false",
    })

    assert "AUTH_PASSWORD still contains a placeholder value." in issues
    assert "SUPABASE_SERVICE_KEY still contains a placeholder value." in issues
    assert "CORS_ALLOWED_ORIGINS still contains a placeholder value." in issues
