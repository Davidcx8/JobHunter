"""
Glassdoor Scraper para JobHunter Pro
Busca ofertas en Glassdoor mediante BeautifulSoup y fallback simulado.
"""

import requests
from bs4 import BeautifulSoup
import logging
import random
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class GlassdoorScraper:
    """Scraper para Glassdoor con fallback de simulación"""
    
    BASE_URL = "https://www.glassdoor.com/Job/jobs.htm"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
    def search(self, keywords: str, location: str = "remote", limit: int = 20) -> List[Dict]:
        """Busca ofertas de trabajo en Glassdoor"""
        jobs = []
        params = {
            'sc.keyword': keywords,
            'locT': 'C',
            'locN': location
        }
        
        logger.info(f"Querying Glassdoor with keywords: {keywords}, location: {location}")
        used_fallback = False
        
        try:
            # Glassdoor heavily blocks scraping, but we try standard parsing
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.select('.react-job-listing, li[data-test="jobListing"]')
                
                logger.info(f"Glassdoor HTML parsing found {len(cards)} card elements")
                
                for card in cards:
                    try:
                        title_el = card.select_one('[data-test="job-title"], .job-title')
                        title = title_el.get_text(strip=True) if title_el else ""
                        
                        company_el = card.select_one('[data-test="employer-name"], .employer-name')
                        company = company_el.get_text(strip=True) if company_el else "N/A"
                        # Clean ratings from company name (e.g. "TechCorp4.5 ★" -> "TechCorp")
                        if company and len(company) > 3 and company[-3:].replace('.', '').isdigit():
                            company = company[:-3].strip()
                        
                        loc_el = card.select_one('[data-test="location"], .location')
                        loc = loc_el.get_text(strip=True) if loc_el else "Remote"
                        
                        url_el = card.select_one('a[data-test="job-link"], a.job-link')
                        job_url = url_el.get('href', '') if url_el else ""
                        if job_url and job_url.startswith('/'):
                            job_url = "https://www.glassdoor.com" + job_url
                            
                        desc_el = card.select_one('.job-description-snippet')
                        desc = desc_el.get_text(strip=True) if desc_el else f"Posición de {title} en {company}."
                        
                        rating_el = card.select_one('.rating-number')
                        rating = rating_el.get_text(strip=True) if rating_el else "3.8"
                        
                        if title and company:
                            jobs.append({
                                'title': title,
                                'company': company,
                                'location': loc,
                                'url': job_url or f"https://www.glassdoor.com/job/mock-{random.randint(100,999)}",
                                'source': 'glassdoor',
                                'posted_date': "Recent",
                                'company_rating': rating,
                                'description': desc,
                                'requirements': ""
                            })
                    except Exception as inner_e:
                        logger.error(f"Error parsing Glassdoor single job card: {inner_e}")
                        continue
            else:
                logger.warning(f"Glassdoor scraper blocked or failed (HTTP {response.status_code})")
                
        except Exception as e:
            logger.error(f"Error scraping Glassdoor: {e}")
            
        if not jobs:
            logger.info("Falling back to simulated Glassdoor jobs.")
            used_fallback = True
            jobs = self._generate_sample_jobs(keywords, limit)

        scrape_mode = "demo" if used_fallback else "live"
        for job in jobs:
            job.setdefault("is_live", not used_fallback)
            job.setdefault("scrape_mode", scrape_mode)
            job.setdefault("scraped_at", datetime.now().isoformat())

        return jobs[:limit]
        
    def _generate_sample_jobs(self, keywords: str, limit: int) -> List[Dict]:
        """Generador de datos de fallback simulados para Glassdoor"""
        sample_jobs = []
        titles = [
            "Software Architect", "Technical Team Lead", "Senior Python Engineer",
            "Data Engineer", "Machine Learning Engineer"
        ]
        companies = ["Airbnb", "Netflix", "Spotify", "Hulu", "Adobe"]
        locations = ["Remote, US", "Seattle, WA", "New York, NY"]
        ratings = ["4.1", "4.3", "4.6", "3.9", "4.2"]
        
        import random
        for i in range(min(limit, 8)):
            title = random.choice(titles)
            if "python" in keywords.lower() and "Python" not in title:
                title = f"{title} (Python)"
                
            sample_jobs.append({
                'title': title,
                'company': random.choice(companies),
                'location': random.choice(locations),
                'url': f"https://www.glassdoor.com/job/mockglassdoor{100+i}",
                'source': 'glassdoor',
                'posted_date': f"Hace {random.randint(1, 7)} días",
                'company_rating': random.choice(ratings),
                'description': f"Coincidencia para búsqueda '{keywords}'. Buscamos profesionales excepcionales para liderar el diseño de sistemas y desarrollo backend modular.",
                'requirements': "Python, SQL, Microservices, System Design"
            })
        return sample_jobs
