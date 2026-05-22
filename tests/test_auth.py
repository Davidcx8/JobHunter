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
