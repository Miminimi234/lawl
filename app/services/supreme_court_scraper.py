"""
Scrape REAL cases from supremecourt.gov and federal courts
No API key needed - public information
"""
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class SupremeCourtScraper:
    """Scrape real Supreme Court opinions from supremecourt.gov"""
    
    SCOTUS_URL = "https://www.supremecourt.gov/opinions/slipopinion/24"
    JUSTIA_SCOTUS = "https://supreme.justia.com/cases/federal/us/"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def get_recent_scotus_cases(self, limit: int = 20) -> List[Dict]:
        """Get recent Supreme Court cases from Justia"""
        cases = []
        
        try:
            # Try recent years
            for year in [2024, 2023, 2022]:
                url = f"https://supreme.justia.com/cases/federal/us/year/{year}/"
                
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find case links
                case_links = soup.find_all('a', href=re.compile(r'/cases/federal/us/\d+/'))
                
                for link in case_links[:limit]:
                    case_title = link.text.strip()
                    case_url = link['href']
                    if not case_url.startswith('http'):
                        case_url = 'https://supreme.justia.com' + case_url
                    
                    # Extract case number from URL
                    match = re.search(r'/us/(\d+)/([^/]+)/', case_url)
                    if match:
                        volume = match.group(1)
                        case_name = case_title
                        
                        cases.append({
                            'title': case_name,
                            'citation': f"{volume} U.S. ___ ({year})",
                            'court': 'Supreme Court of the United States',
                            'jurisdiction': 'Federal - Supreme Court',
                            'url': case_url,
                            'year': year
                        })
                    
                    if len(cases) >= limit:
                        break
                
                if len(cases) >= limit:
                    break
                
                time.sleep(0.5)
            
            logger.info(f"Scraped {len(cases)} SCOTUS cases")
            return cases
            
        except Exception as e:
            logger.error(f"SCOTUS scraping error: {e}")
            return []
    
    def get_case_text(self, case_url: str) -> str:
        """Scrape full case text from Justia"""
        try:
            response = requests.get(case_url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find case body
            case_body = soup.find('div', class_='casebody') or soup.find('div', id='opinion')
            
            if case_body:
                text = case_body.get_text(separator='\n', strip=True)
                return text[:15000]  # First 15k chars
            
            # Fallback: get all paragraphs
            paragraphs = soup.find_all('p')
            text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs[:50]])
            return text[:15000]
            
        except Exception as e:
            logger.error(f"Error scraping case text: {e}")
            return ""


class FederalCourtScraper:
    """Scrape recent federal circuit court opinions"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def get_ninth_circuit_cases(self, limit: int = 10) -> List[Dict]:
        """Get recent 9th Circuit opinions from ca9.uscourts.gov"""
        cases = []
        
        try:
            # 9th Circuit opinions page
            url = "https://cdn.ca9.uscourts.gov/datastore/opinions/"
            
            # Recent months
            from datetime import datetime
            current_year = datetime.now().year
            
            for month in range(1, 13):
                month_url = f"{url}{current_year}/{month:02d}/"
                
                try:
                    response = requests.get(month_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find PDF links
                        links = soup.find_all('a', href=re.compile(r'\.pdf$'))
                        
                        for link in links[:5]:
                            filename = link.text.strip()
                            
                            # Extract case info from filename (e.g., "23-1234.pdf")
                            match = re.search(r'(\d{2})-(\d+)', filename)
                            if match:
                                cases.append({
                                    'title': f"Case No. {match.group(1)}-{match.group(2)}",
                                    'citation': f"{match.group(1)}-{match.group(2)} (9th Cir. {current_year})",
                                    'court': '9th Circuit Court of Appeals',
                                    'jurisdiction': 'Federal - 9th Circuit',
                                    'url': month_url + link['href'],
                                    'year': current_year
                                })
                        
                        if len(cases) >= limit:
                            break
                except:
                    continue
            
            return cases[:limit]
            
        except Exception as e:
            logger.error(f"9th Circuit scraping error: {e}")
            return []


def get_real_cases_mix(limit: int = 50) -> List[Dict]:
    """Get a mix of real cases from multiple sources"""
    all_cases = []
    
    print("   🏛️  Scraping Supreme Court opinions...")
    scotus_scraper = SupremeCourtScraper()
    scotus_cases = scotus_scraper.get_recent_scotus_cases(limit=30)
    all_cases.extend(scotus_cases)
    
    print(f"   ✅ Found {len(scotus_cases)} Supreme Court cases")
    
    time.sleep(1)
    
    print("   🏛️  Scraping 9th Circuit opinions...")
    circuit_scraper = FederalCourtScraper()
    circuit_cases = circuit_scraper.get_ninth_circuit_cases(limit=20)
    all_cases.extend(circuit_cases)
    
    print(f"   ✅ Found {len(circuit_cases)} Circuit Court cases")
    
    return all_cases[:limit]

