import re
from typing import List, Dict, Any, Tuple

class MatchingEngine:
    @staticmethod
    def clean_text(text: str) -> str:
        """Helper to lowercase and clean symbols from text for better word matching"""
        if not text:
            return ""
        # Lowercase and replace common punctuation with spaces
        cleaned = text.lower()
        cleaned = re.sub(r'[\/\\(),\.\-\:\;\!\?\"\'•]', ' ', cleaned)
        return " " + " ".join(cleaned.split()) + " "

    @classmethod
    def calculate_score(cls, 
                        job_title: str, 
                        job_description: str, 
                        job_requirements: str, 
                        user_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """
        Calculates a match score from 0 to 100.
        Returns: (score, matching_skills, missing_skills)
        """
        if not user_skills:
            return 0.0, [], []

        # Clean all text components
        title_clean = cls.clean_text(job_title)
        desc_clean = cls.clean_text(job_description)
        reqs_clean = cls.clean_text(job_requirements)
        
        combined_body_clean = desc_clean + " " + reqs_clean

        matching_skills = []
        missing_skills = []

        # Find matching skills using boundary-safe word matching
        for skill in user_skills:
            skill_clean = skill.strip().lower()
            if not skill_clean:
                continue
            
            # Use regex with word boundaries or space padding to find exact skill occurrences
            # This avoids matching "Go" inside "Google" or "Django"
            # We match skill enclosed in boundaries
            escaped_skill = re.escape(skill_clean)
            pattern = re.compile(rf'\b{escaped_skill}\b', re.IGNORECASE)
            
            in_body = bool(pattern.search(combined_body_clean))
            in_title = bool(pattern.search(title_clean))
            
            if in_body or in_title:
                matching_skills.append(skill)
            else:
                missing_skills.append(skill)

        # Math formula:
        # Base weight: 70% based on proportion of matching skills
        # Title bonus: 30% if any matching skill is in the job title
        if not user_skills:
            ratio = 0.0
        else:
            ratio = len(matching_skills) / len(user_skills)
            
        base_score = ratio * 70.0
        
        # Check if any matching skill is in the job title
        has_title_match = False
        for skill in matching_skills:
            escaped_skill = re.escape(skill.strip().lower())
            pattern = re.compile(rf'\b{escaped_skill}\b', re.IGNORECASE)
            if pattern.search(title_clean):
                has_title_match = True
                break
                
        title_bonus = 30.0 if has_title_match else 0.0
        
        total_score = min(base_score + title_bonus, 100.0)
        
        # Round to 1 decimal place
        return round(total_score, 1), matching_skills, missing_skills
