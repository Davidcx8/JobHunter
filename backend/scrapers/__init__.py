# JobHunter Pro - Scrapers Module
from .linkedin_scraper import LinkedInScraper
from .indeed_scraper import IndeedScraper
from .remotive_scraper import RemotiveScraper
from .glassdoor_scraper import GlassdoorScraper
from .ziprecruiter_scraper import ZipRecruiterScraper
from .weworkremotely_scraper import WeWorkRemotelyScraper

__all__ = [
    'LinkedInScraper',
    'IndeedScraper',
    'RemotiveScraper',
    'GlassdoorScraper',
    'ZipRecruiterScraper',
    'WeWorkRemotelyScraper'
]