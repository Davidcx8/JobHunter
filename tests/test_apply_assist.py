import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def import_main(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "apply.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("main")


def test_apply_assist_identifies_platform_and_candidate_packet(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)
    main.db.save_profile(
        {
            "full_name": "Jose David Castillo",
            "email": "jose@example.com",
            "phone": "+1 809 000 0000",
            "location": "Remote",
            "linkedin_url": "https://linkedin.com/in/jose",
            "github_url": "https://github.com/Davidcx8",
            "portfolio_url": "https://portfolio.example",
            "skills": ["Python", "FastAPI"],
        }
    )
    job = main.db.add_job(
        {
            "title": "Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "url": "https://jobs.lever.co/acme/abc123",
            "source": "linkedin",
        }
    )
    client = TestClient(main.app)

    response = client.get(f"/api/jobs/{job['id']}/apply-assist")

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "lever"
    assert payload["apply_url"] == "https://jobs.lever.co/acme/abc123"
    assert payload["automation_level"] == "assisted"
    assert payload["candidate"]["full_name"] == "Jose David Castillo"
    assert payload["candidate"]["links"]["github"] == "https://github.com/Davidcx8"
    assert "Open the Lever hosted application form" in payload["steps"][0]


def test_apply_assist_rejects_missing_job(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.get("/api/jobs/999999/apply-assist")

    assert response.status_code == 404
