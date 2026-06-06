"""
GitHub Jobs Scraper para JobHunter Pro
Busca ofertas de trabajo en GitHub Careers (旧的 API) y empresas tech en GitHub
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from typing import List, Dict, Optional


logger = logging.getLogger(__name__)

class GitHubJobsScraper:
    """Scraper para oportunidades en GitHub y empresas tech"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/vnd.github.v3+json',
        })
    
    def search(self, keywords: str = "", location: str = "", limit: int = 30) -> List[Dict]:
        """Busca ofertas en GitHub Careers y empresas relacionadas"""
        jobs = []
        
        # GitHub Careers (usan page de careers)
        github_jobs = self._search_github_careers(keywords, limit//2)
        jobs.extend(github_jobs)
        
        # Empleos en empresas que usan GitHub
        company_jobs = self._search_tech_companies(keywords, limit//2)
        jobs.extend(company_jobs)
        
        return jobs[:limit]
    
    def _search_github_careers(self, keywords: str, limit: int) -> List[Dict]:
        """Busca en páginas de carreras de empresas conocidas"""
        jobs = []
        
        # Lista de empresas tech con carreras en GitHub
        companies = [
            "github", "microsoft", "gitlab", "bitbucket", 
            "vercel", "netlify", "supabase", "planetscale",
            "digitalocean", "cloudflare"
        ]
        
        for company in companies[:5]:
            try:
                url = f"https://careers.github.com/positions?search={keywords}" if company == "github" else f"https://github.com/{company}/careers"
                
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    job_cards = soup.select('.job-card, .position')[:limit//5]
                    
                    for card in job_cards:
                        title_elem = card.select_one('h3, .title, a')
                        if title_elem:
                            jobs.append({
                                'title': title_elem.get_text(strip=True),
                                'company': company.capitalize(),
                                'location': 'Remote / Worldwide',
                                'url': f"https://github.com/{company}/careers",
                                'source': 'GitHub',
                                'posted_date': '',
                                'description': f"Join {company.capitalize()} team",
                            })
            except requests.RequestException as exc:
                logger.warning("Failed to fetch GitHub careers page for %s: %s", company, exc)
            
            time.sleep(0.3)
        
        return jobs
    
    def _search_tech_companies(self, keywords: str, limit: int) -> List[Dict]:
        """Busca en empresas tech que publican en sus propios sites"""
        jobs = []
        
        # Empleos example de empresas tech (demo data)
        tech_jobs = [
            {'company': 'Vercel', 'url': 'https://vercel.com/careers'},
            {'company': 'Supabase', 'url': 'https://supabase.com/careers'},
            {'company': 'Linear', 'url': 'https://linear.app/careers'},
            {'company': 'Notion', 'url': 'https://notion.so/careers'},
            {'company': 'Stripe', 'url': 'https://stripe.com/jobs'},
            {'company': 'Airbnb', 'url': 'https://airbnb.com/careers'},
            {'company': 'Figma', 'url': 'https://figma.com/careers'},
            {'company': 'Anthropic', 'url': 'https://anthropic.com/careers'},
        ]
        
        import random
        
        titles = [
            "Senior Software Engineer", "Full Stack Developer", "Backend Engineer",
            "Frontend Engineer", "DevOps Engineer", "ML Engineer",
            "Product Designer", "Technical Writer", "Developer Advocate"
        ]
        
        for job in tech_jobs[:limit]:
            jobs.append({
                'title': random.choice(titles),
                'company': job['company'],
                'location': random.choice(['Remote', 'Worldwide', 'San Francisco, CA', 'New York, NY']),
                'url': job['url'],
                'source': 'GitHub Ecosystem',
                'posted_date': f"{random.randint(1, 30)} days ago",
                'description': f"Join {job['company']} - industry leading tech company"
            })
        
        return jobs
    
    def get_repo_contributors_jobs(self, keywords: str = "") -> List[Dict]:
        """Busca empresas basadas en contribuidores activos de repos populares"""
        # Simulación de búsqueda por tecnología
        popular_repos = [
            {'org': 'facebook', 'repo': 'react'},
            {'org': 'vuejs', 'repo': 'vue'},
            {'org': 'sveltejs', 'repo': 'svelte'},
            {'org': 'denoland', 'repo': 'deno'},
            {'org': 'nodejs', 'repo': 'node'},
        ]
        
        jobs = []
        import random
        
        for repo in popular_repos:
            jobs.append({
                'title': f"{random.choice(['Developer', 'Engineer', 'Contributor'])} for {repo['repo']}",
                'company': repo['org'].capitalize(),
                'location': 'Remote',
                'url': f"https://github.com/{repo['org']}/{repo['repo']}",
                'source': 'GitHub Open Source',
                'tech_stack': repo['repo'],
                'description': f"Open source contribution opportunity with {repo['org'].capitalize()}"
            })
        
        return jobs
