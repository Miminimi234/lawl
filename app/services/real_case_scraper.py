"""
Scrape REAL court cases from public sources - NO API KEYS NEEDED
"""
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict
import logging
import re

logger = logging.getLogger(__name__)

class RealCaseScraper:
    """Scrape real cases from multiple public sources"""
    
    def get_supreme_court_cases(self, limit: int = 20) -> List[Dict]:
        """Scrape recent Supreme Court opinions from supremecourt.gov"""
        cases = []
        
        try:
            # Supreme Court opinions page
            url = "https://www.supremecourt.gov/opinions/slipopinion/22"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find opinion links
            for link in soup.find_all('a', href=True)[:limit]:
                if link['href'].endswith('.pdf'):
                    case_name = link.text.strip()
                    if ' v. ' in case_name or ' v ' in case_name:
                        cases.append({
                            'title': case_name,
                            'court': 'Supreme Court of the United States',
                            'jurisdiction': 'Federal',
                            'citation': f"__ U.S. __ (2024)",
                            'case_type': 'general',
                            'url': f"https://www.supremecourt.gov{link['href']}",
                            'snippet': f"Supreme Court opinion: {case_name}"
                        })
            
            logger.info(f"Scraped {len(cases)} Supreme Court cases")
            return cases
            
        except Exception as e:
            logger.error(f"Supreme Court scraping error: {e}")
            return []
    
    def get_ca9_cases(self, limit: int = 20) -> List[Dict]:
        """Scrape 9th Circuit opinions"""
        cases = []
        
        try:
            url = "https://cdn.ca9.uscourts.gov/datastore/opinions/2024/"
            # This is tricky without an index, so let's use a different approach
            # Get from their RSS feed
            rss_url = "https://www.ca9.uscourts.gov/media/view_rss.php?pk_id=0000000"
            
            response = requests.get("https://www.ca9.uscourts.gov/opinions/", timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for opinion listings
            for row in soup.find_all('tr')[:limit]:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    case_name = cells[0].text.strip()
                    if ' v. ' in case_name or ' v ' in case_name:
                        cases.append({
                            'title': case_name,
                            'court': '9th Circuit Court of Appeals',
                            'jurisdiction': '9th Circuit',
                            'citation': f"__ F.4th __ (9th Cir. 2024)",
                            'case_type': 'general',
                            'snippet': f"9th Circuit opinion: {case_name}"
                        })
            
            logger.info(f"Scraped {len(cases)} 9th Circuit cases")
            return cases
            
        except Exception as e:
            logger.error(f"9th Circuit scraping error: {e}")
            return []
    
    def get_justia_recent_cases(self, limit: int = 30) -> List[Dict]:
        """Scrape recent federal appellate cases from Justia"""
        cases = []
        
        try:
            # Justia recent opinions
            urls = [
                "https://law.justia.com/cases/federal/appellate-courts/ca9/",
                "https://law.justia.com/cases/federal/appellate-courts/ca2/",
                "https://law.justia.com/cases/federal/appellate-courts/ca5/"
            ]
            
            for base_url in urls:
                if len(cases) >= limit:
                    break
                    
                try:
                    response = requests.get(base_url, timeout=15)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find case links
                    for link in soup.find_all('a', href=True):
                        if '/cases/federal/appellate-courts/' in link['href']:
                            case_name = link.text.strip()
                            if ' v. ' in case_name and len(case_name) > 10 and len(case_name) < 200:
                                # Extract circuit from URL
                                circuit_match = re.search(r'/ca(\d+)/', link['href'])
                                circuit = f"{circuit_match.group(1)}th Circuit" if circuit_match else "Federal Circuit"
                                
                                cases.append({
                                    'title': case_name,
                                    'court': f"{circuit} Court of Appeals",
                                    'jurisdiction': circuit,
                                    'citation': 'F.4th',
                                    'case_type': 'general',
                                    'url': link['href'] if link['href'].startswith('http') else f"https://law.justia.com{link['href']}",
                                    'snippet': f"{circuit} opinion: {case_name}"
                                })
                                
                                if len(cases) >= limit:
                                    break
                    
                    time.sleep(1)  # Be respectful
                    
                except Exception as e:
                    logger.warning(f"Error scraping {base_url}: {e}")
                    continue
            
            logger.info(f"Scraped {len(cases)} Justia cases")
            return cases
            
        except Exception as e:
            logger.error(f"Justia scraping error: {e}")
            return []
    
    def get_diverse_real_cases(self, limit: int = 50) -> List[Dict]:
        """Get diverse real cases from multiple sources"""
        all_cases = []
        
        print("   🏛️  Scraping Supreme Court opinions...")
        supreme = self.get_supreme_court_cases(limit=10)
        all_cases.extend(supreme)
        
        time.sleep(2)
        
        print("   ⚖️  Scraping Federal Circuit opinions from Justia...")
        justia = self.get_justia_recent_cases(limit=40)
        all_cases.extend(justia)
        
        # Remove duplicates
        seen = set()
        unique = []
        for case in all_cases:
            title = case['title'].lower()
            if title not in seen and len(title) > 5:
                seen.add(title)
                unique.append(case)
        
        logger.info(f"Total real cases scraped: {len(unique)}")
        return unique[:limit]

