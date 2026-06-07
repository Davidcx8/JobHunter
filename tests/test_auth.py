import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def test_auth_enabled_protects_api_and_accepts_valid_login(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD", "testpass")
    monkeypatch.setenv("AUTH_SECRET_KEY", "testsecret")
    monkeypatch.setenv("AUTH_RETURN_BEARER_TOKEN", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "auth_validation.db"))

    for module_name in ["settings", "main"]:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    client = TestClient(main.app)

    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/auth/config").json()["auth_enabled"] is True
    assert client.post("/api/auth/login", json={"username": "admin", "password": "bad"}).status_code == 401

    login = client.post("/api/auth/login", json={"username": "admin", "password": "testpass"})
    assert login.status_code == 200
    token = login.json()["token"]

    authorized = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert authorized.status_code == 200
    assert authorized.json()["profile"]["id"] == "default"


def test_production_configuration_reports_insecure_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "null,http://localhost:8000")

    for module_name in ["settings"]:
        sys.modules.pop(module_name, None)

    settings_module = importlib.import_module("settings")
    issues = settings_module.settings.validate_runtime_configuration()

    assert "AUTH_ENABLED must be true in production." in issues
    assert "AUTH_COOKIE_SECURE must be true in production." in issues
    assert "CORS_ALLOWED_ORIGINS must not include null in production." in issues
    assert "CORS_ALLOWED_ORIGINS must not include localhost origins in production." in issues


def test_production_configuration_rejects_placeholder_values(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PASSWORD", "replace-with-a-long-random-password")
    monkeypatch.setenv("AUTH_SECRET_KEY", "replace-with-a-long-random-secret")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_RETURN_BEARER_TOKEN", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://your-domain.example")
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "replace-with-service-role-key")

    for module_name in ["settings"]:
        sys.modules.pop(module_name, None)

    settings_module = importlib.import_module("settings")
    issues = settings_module.settings.validate_runtime_configuration()

    assert "AUTH_PASSWORD must not use a placeholder value in production." in issues
    assert "SUPABASE_SERVICE_KEY must not use a placeholder value in production." in issues
    assert "CORS_ALLOWED_ORIGINS must not use placeholder origins in production." in issues


def test_login_rate_limits_failures_and_cookie_auth_does_not_return_token(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD", "testpass")
    monkeypatch.setenv("AUTH_SECRET_KEY", "testsecret")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES", "2")
    monkeypatch.setenv("AUTH_LOGIN_LOCKOUT_SECONDS", "60")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "auth_rate_limit.db"))

    for module_name in ["settings", "main"]:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    client = TestClient(main.app)

    assert client.post("/api/auth/login", json={"username": "admin", "password": "bad-1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "admin", "password": "bad-2"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "admin", "password": "bad-3"}).status_code == 429
    assert client.post("/api/auth/login", json={"username": "admin", "password": "testpass"}).status_code == 429

    main.login_rate_limiter.reset()
    login = client.post("/api/auth/login", json={"username": "admin", "password": "testpass"})
    assert login.status_code == 200
    assert "token" not in login.json()
    assert "jobhunter_session" in login.headers.get("set-cookie", "")


def test_authenticated_user_can_change_password_without_redeploy(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD", "old-password")
    monkeypatch.setenv("AUTH_SECRET_KEY", "testsecret")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "auth_change.db"))

    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    client = TestClient(main.app)

    assert client.post(
        "/api/auth/change-password",
        json={"current_password": "old-password", "new_password": "new-password"},
    ).status_code == 401

    login = client.post("/api/auth/login", json={"username": "admin", "password": "old-password"})
    assert login.status_code == 200

    wrong_current = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "new-password"},
    )
    assert wrong_current.status_code == 401

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "old-password", "new_password": "new-password"},
    )
    assert changed.status_code == 200
    assert changed.json()["success"] is True

    assert client.post("/api/auth/login", json={"username": "admin", "password": "old-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "admin", "password": "new-password"}).status_code == 200
