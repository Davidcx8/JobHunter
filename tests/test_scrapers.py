import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Adjust path to find backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from scrapers.weworkremotely_scraper import WeWorkRemotelyScraper
from scrapers.remotive_scraper import RemotiveScraper
from scrapers.linkedin_scraper import LinkedInScraper

class TestScrapers(unittest.TestCase):
    @patch('requests.Session.get')
    def test_weworkremotely_rss_parsing(self, mock_get):
        # Mock XML response for WeWorkRemotely RSS feed
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>We Work Remotely: Programming Jobs</title>
                <link>https://weworkremotely.com/</link>
                <item>
                    <title>Stripe: Senior Python Developer</title>
                    <link>https://weworkremotely.com/remote-jobs/stripe-senior-python</link>
                    <description>&lt;p&gt;Looking for a developer to write payment code.&lt;/p&gt;</description>
                    <pubDate>Wed, 20 May 2026 12:00:00 +0000</pubDate>
                </item>
            </channel>
        </rss>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = xml_content.encode('utf-8')
        mock_get.return_value = mock_response
        
        scraper = WeWorkRemotelyScraper()
        results = scraper.search(limit=1)
        
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job['company'], 'Stripe')
        self.assertEqual(job['title'], 'Senior Python Developer')
        self.assertEqual(job['source'], 'weworkremotely')
        self.assertIn('payment code', job['description'])

    @patch('requests.Session.get')
    def test_remotive_api_parsing(self, mock_get):
        # Mock JSON response for Remotive API
        json_data = {
            "jobs": [
                {
                    "title": "React Frontend Engineer",
                    "company_name": "WebSaaS",
                    "candidate_required_location": "Europe",
                    "url": "https://remotive.com/jobs/react-frontend",
                    "salary": "$90,000",
                    "publication_date": "2026-05-20T10:00:00",
                    "description": "<p>Build SaaS dashboards in React.</p>"
                }
            ]
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_data
        mock_get.return_value = mock_response
        
        scraper = RemotiveScraper()
        results = scraper.search(limit=1)
        
        self.assertEqual(len(results), 1)
        job = results[0]
        self.assertEqual(job['company'], 'WebSaaS')
        self.assertEqual(job['title'], 'React Frontend Engineer')
        self.assertEqual(job['location'], 'Europe')
        self.assertIn('SaaS dashboards', job['description'])

    @patch('requests.Session.get')
    def test_scraper_fallback_on_error(self, mock_get):
        # Setup request error (blocked or timeout)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        # LinkedInScraper should handle 403 and fall back to simulated jobs
        scraper = LinkedInScraper()
        results = scraper.search(keywords="Python", limit=5)
        
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['source'], 'linkedin')
        # Check that it filtered or adjusted based on keyword
        self.assertTrue(any("python" in job['title'].lower() for job in results))

if __name__ == "__main__":
    unittest.main()
