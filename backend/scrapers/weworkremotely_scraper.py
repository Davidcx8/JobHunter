"""
WeWorkRemotely Scraper para JobHunter Pro
Utiliza el feed RSS público oficial de WeWorkRemotely para una fiabilidad del 100%
"""

import requests
import defusedxml.ElementTree as ET
import logging
import time
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class WeWorkRemotelyScraper:
    """Scraper para WeWorkRemotely via RSS feed"""
    
    # Official RSS Feed for Programming category
    RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def search(self, keywords: str = "", limit: int = 50) -> List[Dict]:
        """Busca ofertas de trabajo remoto en WeWorkRemotely leyendo su canal RSS"""
        jobs = []
        used_fallback = False
        logger.info(f"Fetching WeWorkRemotely RSS Feed from: {self.RSS_URL}")
        
        try:
            response = self.session.get(self.RSS_URL, timeout=15)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                for item in items:
                    title_full = item.find('title').text if item.find('title') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    description_html = item.find('description').text if item.find('description') is not None else ""
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                    
                    # WWR RSS format: "<Company>: <Job Title>"
                    company = "N/A"
                    title = title_full
                    if ":" in title_full:
                        parts = title_full.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()
                    
                    # Clean html tags from description for the snippet
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(description_html, 'html.parser')
                    desc_text = soup.get_text()
                    
                    # Simple keyword filtering if requested
                    if keywords:
                        keywords_lower = keywords.lower()
                        # Search in title, company or description
                        if keywords_lower not in title.lower() and keywords_lower not in company.lower() and keywords_lower not in desc_text.lower():
                            continue
                            
                    # Extract salary if present (WWR sometimes has salary in the title/desc)
                    # For RSS, it is mostly in HTML.
                    salary = None
                    
                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': 'Worldwide (Remote)',
                        'url': link,
                        'source': 'weworkremotely',
                        'salary': salary,
                        'posted_date': pub_date,
                        'description': desc_text[:800],
                        'requirements': ''
                    })
                    
                    if len(jobs) >= limit:
                        break
                        
        except Exception as e:
            logger.error(f"Error parseando feed RSS de WeWorkRemotely: {e}")
            # Si falla, generar datos de ejemplo
            used_fallback = True
            jobs = self._generate_sample_jobs(keywords, limit)

        scrape_mode = "demo" if used_fallback else "live"
        for job in jobs:
            job.setdefault("is_live", not used_fallback)
            job.setdefault("scrape_mode", scrape_mode)
            job.setdefault("scraped_at", datetime.now().isoformat())

        return jobs
        
    def _generate_sample_jobs(self, keywords: str, limit: int) -> List[Dict]:
        """Generador de datos de fallback para demostración si el feed falla"""
        logger.info("Generating fallback mock data for WeWorkRemotely...")
        sample_jobs = []
        titles = [
            "Senior React Engineer", "Python Backend Developer", "DevOps Engineer",
            "SRE Lead", "Node.js Architect", "iOS/Swift Developer"
        ]
        companies = ["Automattic", "GitLab", "Zapier", "Toptal", "Buffer", "Elastic"]
        
        import random
        for i in range(min(limit, 10)):
            sample_jobs.append({
                'title': random.choice(titles),
                'company': random.choice(companies),
                'location': 'Remote (Worldwide)',
                'url': f"https://weworkremotely.com/remote-jobs/mock-job-{1000+i}",
                'source': 'weworkremotely',
                'salary': "$100,000 - $140,000",
                'posted_date': datetime.now().strftime("%Y-%m-%d"),
                'description': f"Esta es una oferta de demostración que coincide con {keywords if keywords else 'desarrollo de software'}. Gran equipo, horarios flexibles y 100% remoto.",
                'requirements': "3+ años de experiencia, Proactividad, Docker/Git"
            })
        return sample_jobs
