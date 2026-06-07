import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def import_main(monkeypatch, tmp_path, **env):
    defaults = {
        "DB_PATH": str(tmp_path / "email.db"),
        "UPLOAD_DIR": str(tmp_path / "uploads"),
        "AUTH_ENABLED": "false",
    }
    defaults.update(env)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("main")


def test_generate_outreach_email_uses_groq_when_configured(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path, GROQ_API_KEY="gsk-test", GROQ_MODEL="llama-3.3-70b-versatile")
    main.db.save_profile(
        {
            "full_name": "David Candidate",
            "headline": "Backend Python Developer",
            "email": "david@example.com",
            "github_url": "https://github.com/david",
            "linkedin_url": "https://linkedin.com/in/david",
            "portfolio_url": "https://david.dev",
            "skills": ["Python", "FastAPI", "Supabase"],
        }
    )
    job = main.db.add_job(
        {
            "title": "Python Developer",
            "company": "Acme",
            "location": "Remote",
            "url": "https://acme.example/jobs/py",
            "description": "Build FastAPI services.",
            "requirements": "Python, FastAPI",
            "source": "manual",
        }
    )

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "Subject: David Candidate <> Python Developer at Acme\n\n"
                                "Hola equipo de Acme,\n\n"
                                "Vi la posición Python Developer y mi experiencia con FastAPI encaja directamente.\n\n"
                                "Saludos,\nDavid"
                            )
                        }
                    }
                ]
            }

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(main.requests, "post", fake_post)
    client = TestClient(main.app)

    response = client.post(
        "/api/email/generate",
        json={
            "contact_email": "recruiter@acme.example",
            "contact_name": "Sara Recruiter",
            "company": "Acme",
            "role": "Recruiter",
            "job_id": job["id"],
            "tone": "direct",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "groq"
    assert payload["subject"] == "David Candidate <> Python Developer at Acme"
    assert "FastAPI" in payload["body"]
    assert captured["url"].endswith("/openai/v1/chat/completions")
    assert captured["payload"]["model"] == "llama-3.3-70b-versatile"
    assert "https://github.com/david" in captured["payload"]["messages"][1]["content"]


def test_generate_outreach_email_falls_back_to_contextual_template(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)
    main.db.save_profile(
        {
            "full_name": "David Candidate",
            "headline": "Backend Python Developer",
            "github_url": "https://github.com/david",
            "linkedin_url": "https://linkedin.com/in/david",
            "skills": ["Python", "FastAPI"],
        }
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/email/generate",
        json={
            "contact_email": "recruiter@example.com",
            "contact_name": "Recruiter",
            "company": "ExampleCo",
            "role": "Talent Partner",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "template"
    assert "David Candidate" in payload["subject"]
    assert "https://github.com/david" in payload["body"]
    assert "Python, FastAPI" in payload["body"]

