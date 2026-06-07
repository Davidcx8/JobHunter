import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def import_main(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "contacts.db"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("main")


def test_delete_contact_removes_contact_and_email_history(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)
    client = TestClient(main.app)
    created = client.post(
        "/api/contacts",
        json={"name": "Delete Me", "email": "delete@example.com", "company": "Acme"},
    ).json()["contact"]
    main.db.add_email_log("delete@example.com", "Hello", "Body", status="simulated")

    response = client.delete(f"/api/contacts/{created['id']}")
    contacts = client.get("/api/contacts").json()["contacts"]
    emails = client.get("/api/emails").json()["emails"]

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert not any(contact.get("id") == created["id"] for contact in contacts)
    assert not any(email.get("contact_id") == created["id"] for email in emails)


def test_delete_missing_contact_returns_404(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.delete("/api/contacts/999999")

    assert response.status_code == 404

