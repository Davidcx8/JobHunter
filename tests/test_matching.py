import os
import sys
import unittest

# Adjust path to find backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from matching_engine import MatchingEngine

class TestMatchingEngine(unittest.TestCase):
    def test_clean_text(self):
        raw = "FastAPI / Python, Developer! SRE (Lead);"
        cleaned = MatchingEngine.clean_text(raw)
        # Should lowercase and separate words by spaces
        self.assertIn(" fastapi ", cleaned)
        self.assertIn(" python ", cleaned)
        self.assertIn(" developer ", cleaned)
        self.assertIn(" sre ", cleaned)
        self.assertIn(" lead ", cleaned)

    def test_calculate_score_exact_match(self):
        user_skills = ["Python", "FastAPI", "React", "Docker"]
        
        # Test case 1: 50% skills match (Python, FastAPI), no title match
        score, matches, missing = MatchingEngine.calculate_score(
            job_title="Software Developer",
            job_description="We build web services using FastAPI and Python.",
            job_requirements="Experience in web frameworks.",
            user_skills=user_skills
        )
        self.assertEqual(len(matches), 2)
        self.assertIn("Python", matches)
        self.assertIn("FastAPI", matches)
        self.assertEqual(len(missing), 2)
        # Score calculation: 2/4 = 50% * 70% = 35.0 (no title bonus)
        self.assertEqual(score, 35.0)

    def test_calculate_score_with_title_bonus(self):
        user_skills = ["Python", "FastAPI", "React"]
        
        # Test case 2: Python is in the title, and Python + React are in the description (2/3 skills match)
        score, matches, missing = MatchingEngine.calculate_score(
            job_title="Senior Python Developer",
            job_description="Must know Python and React.",
            job_requirements="",
            user_skills=user_skills
        )
        self.assertEqual(len(matches), 2)
        # Score math: 2/3 = 66.67% * 70.0 = 46.7% + 30.0 title bonus = 76.7%
        self.assertEqual(score, 76.7)

    def test_word_boundaries(self):
        # We want to make sure it matches "Go" but does not match "Go" inside "Google" or "Django"
        user_skills = ["Go"]
        
        # Scenario A: "Go" inside "Django"
        score, matches, missing = MatchingEngine.calculate_score(
            job_title="Python Developer",
            job_description="We use Django for backend development.",
            job_requirements="",
            user_skills=user_skills
        )
        self.assertEqual(len(matches), 0)
        self.assertEqual(score, 0.0)
        
        # Scenario B: "Go" as a separate word
        score, matches, missing = MatchingEngine.calculate_score(
            job_title="Go Engineer",
            job_description="Write microservices in Go language.",
            job_requirements="",
            user_skills=user_skills
        )
        self.assertEqual(len(matches), 1)
        # 1/1 = 100% * 70% + 30% bonus = 100%
        self.assertEqual(score, 100.0)

    def test_empty_skills(self):
        score, matches, missing = MatchingEngine.calculate_score(
            job_title="Any Job",
            job_description="Some description",
            job_requirements="",
            user_skills=[]
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(matches, [])
        self.assertEqual(missing, [])

if __name__ == "__main__":
    unittest.main()
