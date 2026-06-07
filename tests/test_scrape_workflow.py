import importlib
import os
import sys

from fastapi.testclient import TestClient


BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_PATH not in sys.path:
    sys.path.append(BACKEND_PATH)


def import_main(monkeypatch, tmp_path, **env):
    defaults = {
        "DB_PATH": str(tmp_path / "scrape.db"),
        "UPLOAD_DIR": str(tmp_path / "uploads"),
        "AUTH_ENABLED": "false",
    }
    defaults.update(env)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    for module_name in ["settings", "db_manager", "main"]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("main")


def test_scrape_response_deduplicates_repeated_jobs_and_cleans_keywords(monkeypatch, tmp_path):
    main = import_main(monkeypatch, tmp_path)

    class DuplicateLinkedInScraper:
        def search(self, keywords, limit):
            assert keywords == "Python Developer"
            return [
                {
                    "title": "Python Developer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://example.com/jobs/1?ref=a",
                    "is_live": True,
                },
                {
                    "title": "Python Developer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://example.com/jobs/1?ref=b",
                    "is_live": True,
                },
                {
                    "title": "Python Developer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://different.example/jobs/duplicate",
                    "is_live": True,
                },
                {
                    "title": "Backend Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "url": "https://example.com/jobs/2",
                    "is_live": True,
                },
            ]

    monkeypatch.setattr(main, "LinkedInScraper", DuplicateLinkedInScraper)
    client = TestClient(main.app)

    response = client.post(
        "/api/scrape/linkedin",
        json={"keywords": "Python DeveloperDeveloper", "location": "Remote", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["keywords_normalized"] == "Python Developer"
    assert payload["jobs_found"] == 2
    assert payload["duplicates_removed"] == 2
    assert [job["title"] for job in payload["jobs"]] == ["Python Developer", "Backend Engineer"]

