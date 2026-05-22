"""
ZipRecruiter Scraper para JobHunter Pro
Busca ofertas en ZipRecruiter mediante BeautifulSoup y fallback simulado.
"""

import requests
from bs4 import BeautifulSoup
import logging
import random
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class ZipRecruiterScraper:
    """Scraper para ZipRecruiter con fallback de simulación"""
    
    BASE_URL = "https://www.ziprecruiter.com/candidate/search"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
    def search(self, keywords: str, location: str = "remote", limit: int = 20) -> List[Dict]:
        """Busca ofertas de trabajo en ZipRecruiter"""
        jobs = []
        params = {
            'search': keywords,
            'location': location
        }
        
        logger.info(f"Querying ZipRecruiter with keywords: {keywords}, location: {location}")
        used_fallback = False
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.select('.job_content, .job-result, [id^="job_key_"]')
                
                logger.info(f"ZipRecruiter HTML parsing found {len(cards)} card elements")
                
                for card in cards:
                    try:
                        title_el = card.select_one('.job_title, .just_job_title')
                        title = title_el.get_text(strip=True) if title_el else ""
                        
                        company_el = card.select_one('.company_name, .name')
                        company = company_el.get_text(strip=True) if company_el else "N/A"
                        
                        loc_el = card.select_one('.location, .company_location')
                        loc = loc_el.get_text(strip=True) if loc_el else "Remote"
                        
                        url_el = card.select_one('a.job_link, a.just_job_title')
                        job_url = url_el.get('href', '') if url_el else ""
                        
                        desc_el = card.select_one('.job_snippet, .snippet')
                        desc = desc_el.get_text(strip=True) if desc_el else f"Posición de {title} en {company}."
                        
                        salary_el = card.select_one('.salary, .estimated_salary')
                        salary = salary_el.get_text(strip=True) if salary_el else None
                        
                        if title and company:
                            jobs.append({
                                'title': title,
                                'company': company,
                                'location': loc,
                                'url': job_url or f"https://www.ziprecruiter.com/job/mock-{random.randint(100,999)}",
                                'source': 'ziprecruiter',
                                'posted_date': "Recent",
                                'salary': salary,
                                'description': desc,
                                'requirements': ""
                            })
                    except Exception as inner_e:
                        logger.error(f"Error parsing ZipRecruiter single job card: {inner_e}")
                        continue
            else:
                logger.warning(f"ZipRecruiter scraper blocked or failed (HTTP {response.status_code})")
                
        except Exception as e:
            logger.error(f"Error scraping ZipRecruiter: {e}")
            
        if not jobs:
            logger.info("Falling back to simulated ZipRecruiter jobs.")
            used_fallback = True
            jobs = self._generate_sample_jobs(keywords, limit)

        scrape_mode = "demo" if used_fallback else "live"
        for job in jobs:
            job.setdefault("is_live", not used_fallback)
            job.setdefault("scrape_mode", scrape_mode)
            job.setdefault("scraped_at", datetime.now().isoformat())

        return jobs[:limit]
        
    def _generate_sample_jobs(self, keywords: str, limit: int) -> List[Dict]:
        """Generador de datos de fallback simulados para ZipRecruiter"""
        sample_jobs = []
        titles = [
            "Software Developer II", "Systems Engineer", "Python Developer",
            "Full Stack Developer", "Data Analyst"
        ]
        companies = ["Accenture", "Infosys", "Cognizant", "Capgemini", "Deloitte"]
        locations = ["Remote, US", "Chicago, IL", "Atlanta, GA"]
        salaries = ["$85,000 - $115,000/yr", "$100,000 - $130,000/yr"]
        
        import random
        for i in range(min(limit, 8)):
            title = random.choice(titles)
            if "python" in keywords.lower() and "Python" not in title:
                title = f"{title} (Python)"
                
            sample_jobs.append({
                'title': title,
                'company': random.choice(companies),
                'location': random.choice(locations),
                'url': f"https://www.ziprecruiter.com/job/mockziprecruiter{100+i}",
                'source': 'ziprecruiter',
                'posted_date': f"Hace {random.randint(1, 5)} días",
                'salary': random.choice(salaries),
                'description': f"Coincidencia para búsqueda '{keywords}'. Únete a nuestro equipo consultor para desarrollar soluciones escalables basadas en Python y arquitecturas nativas de nube.",
                'requirements': "Python, Git, REST APIs, SQL"
            })
        return sample_jobs
