"""
Justia.com Web Scraper - REAL court cases, NO API needed
Scrapes actual published federal court opinions
"""
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

class JustiaScraper:
    """Scrape real court cases from Justia.com - completely free and public"""
    
    BASE_URL = "https://law.justia.com"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def get_recent_federal_cases(self, limit: int = 30) -> List[Dict]:
        """Get recent federal appellate cases"""
        cases = []
        
        # Federal circuit courts
        circuits = [
            'first-circuit',
            'second-circuit', 
            'third-circuit',
            'fourth-circuit',
            'fifth-circuit',
            'sixth-circuit',
            'seventh-circuit',
            'eighth-circuit',
            'ninth-circuit',
            'tenth-circuit',
            'eleventh-circuit',
            'dc-circuit'
        ]
        
        per_circuit = max(3, limit // len(circuits))
        
        for circuit in circuits[:4]:  # Just first 4 circuits for speed
            url = f"{self.BASE_URL}/cases/federal/appellate-courts/{circuit}/"
            try:
                print(f"   Scraping {circuit}...")
                circuit_cases = self._scrape_circuit_page(url, limit=per_circuit)
                cases.extend(circuit_cases)
                
                if len(cases) >= limit:
                    break
                    
                time.sleep(2)  # Be polite
                
            except Exception as e:
                logger.error(f"Error scraping {circuit}: {e}")
                continue
        
        return cases[:limit]
    
    def _scrape_circuit_page(self, url: str, limit: int = 5) -> List[Dict]:
        """Scrape a circuit court page for recent cases"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            cases = []
            
            # Find case links
            case_divs = soup.find_all('div', class_='case-title')
            if not case_divs:
                # Try alternative selectors
                case_divs = soup.find_all('h3')
            
            for div in case_divs[:limit]:
                link = div.find('a', href=True)
                if link and '/cases/federal/' in link['href']:
                    case_title = link.text.strip()
                    case_url = link['href']
                    
                    if not case_url.startswith('http'):
                        case_url = self.BASE_URL + case_url
                    
                    # Scrape the full case
                    case_data = self._scrape_case_page(case_url, case_title)
                    if case_data:
                        cases.append(case_data)
                        print(f"      ✅ {case_title[:60]}")
                    
                    time.sleep(1)  # Rate limiting
            
            return cases
            
        except Exception as e:
            logger.error(f"Error scraping circuit page: {e}")
            return []
    
    def _scrape_case_page(self, url: str, title: str) -> Optional[Dict]:
        """Scrape individual case page for full text"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract citation
            citation_elem = soup.find('span', class_='citation')
            citation = citation_elem.text.strip() if citation_elem else 'N/A'
            
            # Extract court
            court_elem = soup.find('div', class_='court-name')
            court = court_elem.text.strip() if court_elem else 'Federal Court'
            
            # Extract date
            date_elem = soup.find('time')
            date_filed = date_elem.get('datetime', '') if date_elem else ''
            
            # Extract case text/opinion
            case_body = soup.find('div', class_='case-text')
            if not case_body:
                case_body = soup.find('article')
            if not case_body:
                case_body = soup.find('div', {'id': 'opinion'})
            
            case_text = ''
            if case_body:
                # Get all paragraphs
                paragraphs = case_body.find_all('p')
                case_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs[:50]])  # First 50 paragraphs
            
            # Fallback: get any text
            if not case_text:
                case_text = soup.get_text(separator='\n', strip=True)[:5000]
            
            # Clean up
            case_text = re.sub(r'\n\s*\n', '\n\n', case_text)  # Remove excess newlines
            case_text = case_text[:10000]  # Limit length
            
            return {
                'title': title,
                'citation': citation,
                'court': court,
                'date_filed': date_filed,
                'case_text': case_text,
                'url': url,
                'snippet': case_text[:500],
                'jurisdiction': court
            }
            
        except Exception as e:
            logger.error(f"Error scraping case {title}: {e}")
            return None
    
    def get_diverse_cases(self, total_limit: int = 30) -> List[Dict]:
        """Get diverse mix of real federal cases"""
        print(f"   🏛️  Scraping Justia.com for REAL federal court opinions...")
        
        cases = self.get_recent_federal_cases(limit=total_limit)
        
        logger.info(f"Justia: Scraped {len(cases)} real court cases")
        return cases

