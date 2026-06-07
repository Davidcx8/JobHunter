"""
Public web jobs API source for JobHunter Pro.

Uses Arbeitnow's public job-board API to avoid brittle HTML scraping where
possible. No API key is required.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebSearchScraper:
    API_URL = "https://arbeitnow.com/api/job-board-api"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "JobHunterPro/4.0 (+https://github.com/Davidcx8/JobHunter)",
                "Accept": "application/json",
            }
        )

    def search(self, keywords: str = "", location: str = "remote", limit: int = 20) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        try:
            response = self.session.get(self.API_URL, timeout=20)
            if response.status_code != 200:
                logger.warning("Arbeitnow API returned status code %s", response.status_code)
                return []
            payload = response.json()
        except Exception as e:
            logger.warning("Failed to query Arbeitnow public jobs API: %s", e)
            return []

        items = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return []

        for item in items:
            normalized = self._normalize_job(item)
            if not self._matches(normalized, keywords, location):
                continue
            jobs.append(normalized)
            if len(jobs) >= limit:
                break
        return jobs

    def _normalize_job(self, item: Dict[str, Any]) -> Dict[str, Any]:
        description_html = str(item.get("description") or "")
        description_text = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        posted_date = item.get("created_at") or item.get("date") or ""
        if isinstance(posted_date, (int, float)):
            posted_date = datetime.fromtimestamp(posted_date, tz=timezone.utc).isoformat()
        return {
            "title": item.get("title") or "",
            "company": item.get("company_name") or item.get("company") or "",
            "location": item.get("location") or ("Remote" if item.get("remote") else ""),
            "url": item.get("url") or item.get("slug") or "",
            "source": "web",
            "salary": "",
            "posted_date": str(posted_date),
            "description": description_text[:800],
            "requirements": ", ".join(str(tag) for tag in tags[:12]),
            "is_live": True,
            "scrape_mode": "live",
            "scraped_at": datetime.now().isoformat(),
        }

    def _matches(self, job: Dict[str, Any], keywords: str, location: str) -> bool:
        haystack = " ".join(
            str(job.get(field) or "")
            for field in ("title", "company", "location", "description", "requirements")
        ).lower()
        keyword_terms = [term.lower() for term in re.split(r"[\s,]+", keywords or "") if len(term.strip()) >= 3]
        location_terms = [term.lower() for term in re.split(r"[\s,]+", location or "") if len(term.strip()) >= 3]
        if keyword_terms and not any(term in haystack for term in keyword_terms):
            return False
        if location_terms and "remote" not in location.lower() and not any(term in haystack for term in location_terms):
            return False
        return True
