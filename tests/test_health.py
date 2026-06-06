import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def import_main(monkeypatch, tmp_path, **env):
    defaults = {
        "DB_PATH": str(tmp_path / "health.db"),
        "UPLOAD_DIR": str(tmp_path / "uploads"),
    }
    defaults.update(env)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("main")


def test_health_is_public_when_auth_is_enabled(monkeypatch, tmp_path):
    main = import_main(
        monkeypatch,
        tmp_path,
        AUTH_ENABLED="true",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="testpass",
        AUTH_SECRET_KEY="testsecret",
    )
    client = TestClient(main.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reports_supabase_unavailable(monkeypatch, tmp_path):
    main = import_main(
        monkeypatch,
        tmp_path,
        STORAGE_BACKEND="supabase",
        SUPABASE_URL="",
        SUPABASE_ANON_KEY="",
        SUPABASE_SERVICE_KEY="",
    )
    client = TestClient(main.app)

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert "Supabase is not configured or unavailable." in response.json()["issues"]
