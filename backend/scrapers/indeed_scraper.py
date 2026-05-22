"""
Indeed Scraper para JobHunter Pro
Busca ofertas en Indeed mediante parsing de HTML y fallback simulado.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class IndeedScraper:
    """Scraper para Indeed con fallback de simulación"""
    
    BASE_URL = "https://www.indeed.com/jobs"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
    def search(self, keywords: str, location: str = "remote", limit: int = 20) -> List[Dict]:
        """Busca ofertas de trabajo en Indeed"""
        jobs = []
        params = {
            'q': keywords,
            'l': location,
            'from': 'web'
        }
        
        logger.info(f"Querying Indeed with keywords: {keywords}, location: {location}")
        used_fallback = False
        
        try:
            # Note: Indeed actively blocks raw requests with Cloudflare
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.select('.job_seen_beacon, .result')
                
                logger.info(f"Indeed HTML parsing found {len(cards)} card elements")
                
                for card in cards:
                    try:
                        title_el = card.select_one('h2.jobTitle span, a.jcs-JobTitle')
                        title = title_el.get_text(strip=True) if title_el else ""
                        
                        company_el = card.select_one('.companyName, span[data-testid="company-name"]')
                        company = company_el.get_text(strip=True) if company_el else "N/A"
                        
                        loc_el = card.select_one('.companyLocation, div[data-testid="text-location"]')
                        loc = loc_el.get_text(strip=True) if loc_el else "Remote"
                        
                        url_el = card.select_one('a.jcs-JobTitle, h2.jobTitle a')
                        jk_id = url_el.get('data-jk') if url_el else ""
                        job_url = f"https://www.indeed.com/viewjob?jk={jk_id}" if jk_id else ""
                        
                        desc_el = card.select_one('.job-snippet, table.jobCard_mainContent')
                        desc = desc_el.get_text(strip=True) if desc_el else f"Posición de {title} en {company}."
                        
                        salary_el = card.select_one('.salary-snippet-container, .metadata.salary-snippet-container')
                        salary = salary_el.get_text(strip=True) if salary_el else None
                        
                        if title and company:
                            jobs.append({
                                'title': title,
                                'company': company,
                                'location': loc,
                                'url': job_url or f"https://www.indeed.com/viewjob?mock={random.randint(100,999)}",
                                'source': 'indeed',
                                'posted_date': "Recent",
                                'salary': salary,
                                'description': desc,
                                'requirements': ""
                            })
                    except Exception as inner_e:
                        logger.error(f"Error parsing Indeed single job card: {inner_e}")
                        continue
            else:
                logger.warning(f"Indeed scraper blocked or failed (HTTP {response.status_code})")
                
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}")
            
        if not jobs:
            logger.info("Falling back to simulated Indeed jobs.")
            used_fallback = True
            jobs = self._generate_sample_jobs(keywords, limit)

        scrape_mode = "demo" if used_fallback else "live"
        for job in jobs:
            job.setdefault("is_live", not used_fallback)
            job.setdefault("scrape_mode", scrape_mode)
            job.setdefault("scraped_at", datetime.now().isoformat())

        return jobs[:limit]
        
    def _generate_sample_jobs(self, keywords: str, limit: int) -> List[Dict]:
        """Generador de datos de fallback simulados para Indeed"""
        sample_jobs = []
        titles = [
            "DevOps Engineer", "Cloud Architect", "Site Reliability Engineer",
            "Python Engineer", "Backend Developer", "Junior Backend Developer"
        ]
        companies = ["Oracle", "Salesforce", "Cisco", "Intel", "IBM", "Red Hat"]
        locations = ["Remote, USA", "Austin, TX", "Denver, CO", "San Jose, CA"]
        salaries = ["$100k - $130k", "$120k - $160k", "$140k - $190k"]
        
        import random
        for i in range(min(limit, 12)):
            title = random.choice(titles)
            if "python" in keywords.lower() and "Python" not in title:
                title = f"Python {title}"
                
            sample_jobs.append({
                'title': title,
                'company': random.choice(companies),
                'location': random.choice(locations),
                'url': f"https://www.indeed.com/viewjob?jk=mockindeed{100+i}",
                'source': 'indeed',
                'posted_date': f"Hace {random.randint(2, 10)} días",
                'salary': random.choice(salaries),
                'description': f"Búsqueda Indeed para '{keywords}'. Buscamos ingenieros motivados para expandir nuestra infraestructura en la nube y optimizar procesos de CI/CD.",
                'requirements': "Python, Docker, AWS, Kubernetes"
            })
        return sample_jobs
