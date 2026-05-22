"""
LinkedIn Jobs Scraper para JobHunter Pro
Busca ofertas de trabajo en LinkedIn utilizando la interfaz pública sin autenticación.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class LinkedInScraper:
    """Scraper para LinkedIn Jobs sin autenticación"""
    
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })
        
    def search(self, keywords: str, location: str = "worldwide", limit: int = 20) -> List[Dict]:
        """Busca ofertas de trabajo en LinkedIn"""
        jobs = []
        params = {
            'keywords': keywords,
            'location': location,
            'f_TPR': 'r2592000',  # Último mes
            'start': 0
        }
        
        logger.info(f"Querying LinkedIn guest jobs with keywords: {keywords}, location: {location}")
        used_fallback = False
        
        try:
            # Fetch public search page (LinkedIn guest jobs seeMoreJobPostings returns an HTML list of <li> elements)
            response = self.session.get(self.BASE_URL, params=params, timeout=12)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                li_elements = soup.select('li')
                
                logger.info(f"LinkedIn seeMoreJobPostings returned {len(li_elements)} elements")
                
                for li in li_elements:
                    try:
                        # Extract title
                        title_el = li.select_one('.base-search-card__title, .job-search-card__title, h3')
                        title = title_el.get_text(strip=True) if title_el else ""
                        
                        # Extract company
                        company_el = li.select_one('.base-search-card__subtitle, .job-search-card__subtitle, a[class*="subtitle"]')
                        company = company_el.get_text(strip=True) if company_el else "N/A"
                        
                        # Extract location
                        loc_el = li.select_one('.job-search-card__location, .base-search-card__metadata span')
                        location_name = loc_el.get_text(strip=True) if loc_el else "Remote"
                        
                        # Extract URL
                        url_el = li.select_one('a.base-card__full-link, a[class*="link"]')
                        job_url = url_el.get('href', '') if url_el else ""
                        if "?" in job_url:
                            job_url = job_url.split("?")[0] # Clean trackers
                            
                        # Extract posted date
                        date_el = li.select_one('time')
                        posted_date = date_el.get_text(strip=True) if date_el else "Recent"
                        
                        if title and company:
                            # Generate a unique job id from URL or random
                            job_id = job_url.split('/view/')[-1] if '/view/' in job_url else str(random.randint(100000, 999999))
                            
                            jobs.append({
                                'title': title,
                                'company': company,
                                'location': location_name,
                                'url': job_url or f"https://www.linkedin.com/jobs/view/{job_id}",
                                'source': 'linkedin',
                                'posted_date': posted_date,
                                'description': f"LinkedIn public listing for {title} position at {company}.",
                                'requirements': ""
                            })
                    except Exception as inner_e:
                        logger.error(f"Error parsing single LinkedIn card: {inner_e}")
                        continue
            else:
                logger.warning(f"LinkedIn scraper blocked / failed (HTTP {response.status_code})")
                
        except Exception as e:
            logger.error(f"Error executing LinkedIn scrape: {e}")
            
        # Fallback to simulated data if blocked or empty results
        if not jobs:
            logger.info("Falling back to simulated LinkedIn jobs.")
            used_fallback = True
            jobs = generate_sample_linkedin_jobs(keywords, limit)

        scrape_mode = "demo" if used_fallback else "live"
        for job in jobs:
            job.setdefault("is_live", not used_fallback)
            job.setdefault("scrape_mode", scrape_mode)
            job.setdefault("scraped_at", datetime.now().isoformat())

        return jobs[:limit]

def generate_sample_linkedin_jobs(keywords: str, limit: int = 20) -> List[Dict]:
    """Genera ofertas de ejemplo basadas en las palabras clave ingresadas por el usuario"""
    sample_jobs = []
    
    titles = [
        "Senior Software Engineer", "Full Stack Developer", "Backend Engineer",
        "Frontend Developer", "DevOps Engineer", "Data Scientist", "Python Developer"
    ]
    
    companies = [
        "Google", "Microsoft", "Amazon", "Meta", "Stripe", "Netflix",
        "Globant", "MercadoLibre", "Uber", "Salesforce"
    ]
    
    locations = ["Remote", "Remote (Latin America)", "San Francisco, CA", "Madrid, Spain", "Austin, TX"]
    salaries = ["$90k - $120k", "$110k - $150k", "$130k - $180k", "$80k - $100k"]
    
    import random
    
    # Filter/Adjust titles based on keywords if matches
    relevant_titles = [t for t in titles if any(kw.lower() in t.lower() for kw in keywords.split())]
    if not relevant_titles:
        relevant_titles = titles
        
    for i in range(min(limit, 15)):
        title = random.choice(relevant_titles)
        if "python" in keywords.lower() and "Python" not in title:
            title = f"{title} (Python)"
            
        sample_jobs.append({
            'title': title,
            'company': random.choice(companies),
            'location': random.choice(locations),
            'url': f"https://www.linkedin.com/jobs/view/{2000000 + i}",
            'source': 'linkedin',
            'posted_date': f"Hace {random.randint(1, 14)} días",
            'salary': random.choice(salaries),
            'description': f"Coincidencia para búsqueda: '{keywords}'. Requerimos habilidades en desarrollo y arquitectura de software, trabajo en equipo y metodologías ágiles.",
            'requirements': ""
        })
        
    return sample_jobs
