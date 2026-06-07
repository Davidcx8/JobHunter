import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def import_main(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "jobs.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("main")


def test_create_job_reuses_existing_semantic_duplicate(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)
    client = TestClient(main.app)
    payload = {
        "title": "Python Developer",
        "company": "Acme",
        "location": "Remote",
        "url": "https://source-a.example/jobs/1",
        "source": "linkedin",
    }

    first = client.post("/api/jobs", json=payload)
    second = client.post(
        "/api/jobs",
        json={**payload, "url": "https://source-b.example/jobs/same-role", "source": "remotive"},
    )
    jobs = client.get("/api/jobs?limit=500").json()["jobs"]
    matching_jobs = [
        job for job in jobs
        if job.get("title") == "Python Developer" and job.get("company") == "Acme"
    ]

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert len(matching_jobs) == 1

