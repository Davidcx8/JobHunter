"""
Remotive Scraper para JobHunter Pro
Busca ofertas de trabajo remoto en Remotive.com via su API pública oficial
"""

import requests
import logging
import time
from typing import List, Dict
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)

class RemotiveScraper:
    """Scraper para la API oficial de Remotive.com"""
    
    API_URL = "https://remotive.com/api/remote-jobs"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        })
        
    def search(self, keywords: str = "", limit: int = 50) -> List[Dict]:
        """Busca ofertas de trabajo remoto en Remotive"""
        jobs = []
        params = {
            'limit': limit
        }
        if keywords:
            params['search'] = keywords
            
        logger.info(f"Querying Remotive API: {self.API_URL} with params: {params}")
        used_fallback = False
        
        try:
            response = self.session.get(self.API_URL, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'jobs' in data:
                    for job in data['jobs']:
                        # Clean html from description
                        desc_html = job.get('description', '')
                        soup = BeautifulSoup(desc_html, 'html.parser')
                        desc_text = soup.get_text()
                        
                        jobs.append({
                            'title': job.get('title', ''),
                            'company': job.get('company_name', ''),
                            'location': job.get('candidate_required_location', 'Remote'),
                            'url': job.get('url', ''),
                            'source': 'remotive',
                            'salary': job.get('salary', ''),
                            'posted_date': job.get('publication_date', ''),
                            'description': desc_text[:800],
                            'requirements': self._extract_requirements(desc_text)
                        })
            else:
                logger.warning(f"Remotive API returned status code {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error querying Remotive API: {e}")
            
        # Fallback to simulated data if no results found
        if not jobs:
            used_fallback = True
            jobs = self._generate_sample_jobs(keywords, limit)

        scrape_mode = "demo" if used_fallback else "live"
        for job in jobs:
            job.setdefault("is_live", not used_fallback)
            job.setdefault("scrape_mode", scrape_mode)
            job.setdefault("scraped_at", datetime.now().isoformat())

        return jobs[:limit]
        
    def _extract_requirements(self, desc_text: str) -> str:
        """Extract lines starting with bullet points or keyword matching requirements"""
        req_lines = []
        lines = desc_text.split('\n')
        for line in lines:
            line_str = line.strip()
            if any(marker in line_str.lower() for marker in ['•', '-', '*', 'experience', 'requirement', 'skill', 'qualification']):
                if len(line_str) > 10 and len(line_str) < 120:
                    req_lines.append(line_str)
            if len(req_lines) >= 5:
                break
        return "\n".join(req_lines)

    def _generate_sample_jobs(self, keywords: str, limit: int) -> List[Dict]:
        """Generador de datos de demostración si la API oficial está lenta/caída"""
        logger.info("Generating fallback mock data for Remotive...")
        sample_jobs = []
        titles = [
            "Senior Backend Engineer (Python)", "Frontend Developer (React)", 
            "Data Scientist", "Lead Django Engineer", "Python Automation Lead"
        ]
        companies = ["Notion", "Figma", "Supabase", "Linear", "Vercel"]
        
        import random
        from datetime import datetime, timedelta
        
        for i in range(min(limit, 10)):
            days_ago = random.randint(0, 5)
            date = datetime.now() - timedelta(days=days_ago)
            
            sample_jobs.append({
                'title': random.choice(titles),
                'company': random.choice(companies),
                'location': 'Worldwide (Remote)',
                'url': f"https://remotive.com/remote-jobs/mock-remotive-{i}",
                'source': 'remotive',
                'salary': "$110,000 - $140,000",
                'posted_date': date.strftime("%Y-%m-%dT%H:%M:%S"),
                'description': f"Coincidencia con {keywords if keywords else 'Python/JS'}. Buscamos una persona para unirse al equipo de ingeniería de producto. Excelente ambiente laboral.",
                'requirements': "• 3+ años de experiencia\n• Fuertes habilidades en Python y bases de datos SQL\n• Comunicación proactiva"
            })
        return sample_jobs
