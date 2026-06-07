import os
import sys
import unittest
import importlib
from datetime import datetime

# Adjust path to find backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from db_manager import DatabaseManager


def test_supabase_primary_does_not_initialize_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-role-key")

    for module_name in ["settings", "db_manager"]:
        sys.modules.pop(module_name, None)

    db_manager = importlib.import_module("db_manager")
    monkeypatch.setattr(db_manager, "SUPABASE_AVAILABLE", True)
    monkeypatch.setattr(db_manager, "create_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        db_manager.DatabaseManager,
        "init_sqlite_tables",
        lambda _self: (_ for _ in ()).throw(AssertionError("SQLite should not initialize")),
    )

    db = db_manager.DatabaseManager(db_path=str(tmp_path / "readonly" / "jobhunter.db"))

    assert db.storage_status == "supabase"

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Create a test database path
        self.db_path = "./data/test_jobhunter.db"
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass
            
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        # Clean up database file after run
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_init_tables(self):
        # Check that we can execute a read and sample data exists
        profile = self.db.get_profile()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.get("id"), "default")
        self.assertEqual(profile.get("full_name"), "Demo Candidate")
        self.assertTrue(any(link.get("label") == "Calendly" for link in profile.get("social_links", [])))

    def test_save_profile(self):
        new_data = {
            "full_name": "Test Tester",
            "email": "test@test.com",
            "skills": ["Python", "FastAPI", "React"],
            "social_links": [{"label": "Blog", "url": "https://example.com/blog"}]
        }
        updated = self.db.save_profile(new_data)
        self.assertEqual(updated.get("full_name"), "Test Tester")
        self.assertEqual(updated.get("email"), "test@test.com")
        self.assertIn("Python", updated.get("skills", []))
        self.assertEqual(updated.get("phone"), "+1 555 0100")
        self.assertEqual(updated.get("social_links")[0].get("label"), "Blog")

    def test_jobs_crud(self):
        job_data = {
            "title": "Software engineer",
            "company": "Amazing Corp",
            "location": "Remote",
            "url": "https://amazing.com/jobs/1",
            "source": "manual",
            "description": "Looking for developers.",
            "requirements": "Python, API",
            "salary": "$90,000",
            "status": "new",
            "match_score": 80.0
        }
        
        # Create
        job = self.db.add_job(job_data)
        self.assertIsNotNone(job.get("id"))
        self.assertEqual(job.get("company"), "Amazing Corp")
        
        # Read
        jobs = self.db.get_jobs()
        self.assertTrue(len(jobs) > 0)
        self.assertTrue(any(j.get("company") == "Amazing Corp" for j in jobs))
        
        # Update
        updated = self.db.update_job(job.get("id"), status="applied", match_score=90.0)
        self.assertEqual(updated.get("status"), "applied")
        self.assertEqual(updated.get("match_score"), 90.0)
        
        # Delete
        self.db.delete_job(job.get("id"))
        jobs_after = self.db.get_jobs()
        self.assertFalse(any(j.get("id") == job.get("id") for j in jobs_after))

    def test_contacts_crud(self):
        contact_data = {
            "name": "Jane recruiter",
            "email": "jane@recruiter.com",
            "company": "RecruitCo",
            "role": "Recruitment Executive",
            "linkedin_url": "https://linkedin.com/in/jane",
            "notes": "Spoke to her yesterday"
        }
        contact = self.db.add_contact(contact_data)
        self.assertIsNotNone(contact.get("id"))
        self.assertEqual(contact.get("name"), "Jane recruiter")
        
        contacts = self.db.get_contacts()
        self.assertTrue(len(contacts) > 0)
        self.assertTrue(any(c.get("email") == "jane@recruiter.com" for c in contacts))

    def test_applications_crud(self):
        app_data = {
            "company": "TechInc",
            "position": "Frontend Lead",
            "status": "applied",
            "applied_date": "2026-05-20",
            "notes": "Sent CV"
        }
        # Create
        app = self.db.add_application(app_data)
        self.assertIsNotNone(app.get("id"))
        self.assertEqual(app.get("company"), "TechInc")
        
        # Read
        apps = self.db.get_applications()
        self.assertTrue(len(apps) > 0)
        self.assertTrue(any(a.get("company") == "TechInc" for a in apps))
        
        # Update
        updated = self.db.update_application(app.get("id"), status="interview", notes="Invited to call")
        self.assertEqual(updated.get("status"), "interview")
        self.assertEqual(updated.get("notes"), "Invited to call")
        
        # Delete
        self.db.delete_application(app.get("id"))
        apps_after = self.db.get_applications()
        self.assertFalse(any(a.get("id") == app.get("id") for a in apps_after))

    def test_documents_crud(self):
        doc_data = {
            "name": "My CV 2026",
            "filename": "cv_2026.pdf",
            "file_type": "cv",
            "file_path": "./data/uploads/cv_2026.pdf",
            "file_size": 1024
        }
        # Create
        doc = self.db.add_document(doc_data)
        self.assertIsNotNone(doc.get("id"))
        self.assertEqual(doc.get("name"), "My CV 2026")
        
        # Read all
        docs = self.db.get_documents()
        self.assertTrue(len(docs) > 0)
        self.assertTrue(any(d.get("name") == "My CV 2026" for d in docs))
        
        # Read single
        single = self.db.get_document(doc.get("id"))
        self.assertIsNotNone(single)
        self.assertEqual(single.get("filename"), "cv_2026.pdf")
        
        # Delete
        self.db.delete_document(doc.get("id"))
        docs_after = self.db.get_documents()
        self.assertFalse(any(d.get("id") == doc.get("id") for d in docs_after))

    def test_metrics(self):
        metrics = self.db.get_dashboard_metrics()
        self.assertIn("jobs", metrics)
        self.assertIn("applications", metrics)
        self.assertIn("contacts", metrics)

if __name__ == "__main__":
    unittest.main()
