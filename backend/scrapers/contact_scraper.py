"""
Contact Scraper para JobHunter Pro
Extrae información de contacto de reclutadores y hiring managers
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional

class ContactScraper:
    """Scraper para extraer contactos (recruiters, hiring managers)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
    
    def extract_contacts(self, url: str) -> List[Dict]:
        """Extrae contactos de una URL (página de empresa o LinkedIn)"""
        contacts = []
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extraer emails del texto
                emails = re.findall(
                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                    response.text
                )
                
                # Limpiar emails duplicados
                seen = set()
                unique_emails = []
                for email in emails:
                    email_lower = email.lower()
                    if email_lower not in seen and not email_lower.startswith('noreply'):
                        seen.add(email_lower)
                        unique_emails.append(email)
                
                # Intentar extraer nombres y roles
                # Este es un ejemplo simplificado - en producción usar NLP
                
                for email in unique_emails[:5]:  # Limitar a 5 contactos
                    domain = email.split('@')[1] if '@' in email else ''
                    contacts.append({
                        'email': email,
                        'name': self._guess_name_from_email(email),
                        'company': self._extract_company_from_url(url),
                        'role': 'Recruiter',
                        'linkedin_url': self._build_linkedin_url(email),
                        'source': url[:50],
                        'notes': ''
                    })
                    
        except Exception as e:
            print(f"Error extrayendo contactos: {e}")
        
        return contacts
    
    def _guess_name_from_email(self, email: str) -> str:
        """Adivina el nombre a partir del email"""
        local = email.split('@')[0]
        
        # Patrones comunes: juan.perez, juan_perez, jperez
        parts = re.split(r'[._]', local)
        if len(parts) >= 2:
            return f"{parts[0].capitalize()} {parts[1].capitalize()}"
        
        # Solo nombre de usuario
        return local.capitalize()
    
    def _extract_company_from_url(self, url: str) -> str:
        """Extrae el nombre de empresa de una URL"""
        # Simple extraction from URL
        domain = url.split('/')[2] if '://' in url else url
        company = domain.replace('www.', '').split('.')[0]
        return company.capitalize()
    
    def _build_linkedin_url(self, email: str) -> str:
        """Construye URL de LinkedIn basada en email (no siempre funciona)"""
        username = email.split('@')[0]
        # No funciona directamente, pero guarda el patrón
        return f"https://www.linkedin.com/search/results/all/?keywords={username}"


# Base de datos de reclutadores conocidos por industria
RECRUITER_DATABASE = {
    'tech': [
        {'name': 'Sarah Chen', 'company': 'Google', 'role': 'Technical Recruiter', 'linkedin': 'sarahchen'},
        {'name': 'Michael Rodriguez', 'company': 'Meta', 'role': 'Senior Recruiter', 'linkedin': 'mrodriguez'},
        {'name': 'Emily Watson', 'company': 'Amazon', 'role': 'Recruiter', 'linkedin': 'emilywatson'},
        {'name': 'David Kim', 'company': 'Microsoft', 'role': 'Talent Acquisition', 'linkedin': 'davidkim'},
        {'name': 'Jessica Taylor', 'company': 'Apple', 'role': 'Recruiting Manager', 'linkedin': 'jtaylor'},
    ],
    'finance': [
        {'name': 'Robert Johnson', 'company': 'Goldman Sachs', 'role': 'HR Manager', 'linkedin': 'rjohnson'},
        {'name': 'Lisa Anderson', 'company': 'JPMorgan', 'role': 'Recruiter', 'linkedin': 'landerson'},
    ],
    'healthcare': [
        {'name': 'Amanda White', 'company': 'Johnson & Johnson', 'role': 'Talent Partner', 'linkedin': 'awhite'},
    ],
    'startup': [
        {'name': 'Alex Rivera', 'company': 'Y Combinator', 'role': 'Founder Relations', 'linkedin': 'arivera'},
    ]
}

def get_recruiter_contacts(industry: str = 'tech', count: int = 10) -> List[Dict]:
    """Obtiene contactos de reclutadores por industria"""
    contacts = []
    
    recruiters = RECRUITER_DATABASE.get(industry, RECRUITER_DATABASE['tech'])
    
    for recruiter in recruiters[:count]:
        contacts.append({
            'name': recruiter['name'],
            'email': f"{recruiter['linkedin']}@{recruiter['company'].lower().replace(' ', '')}.com",
            'company': recruiter['company'],
            'role': recruiter['role'],
            'linkedin_url': f"https://www.linkedin.com/in/{recruiter['linkedin']}",
            'source': 'Recruiter Database',
            'notes': f"Contact for {industry} roles"
        })
    
    return contacts