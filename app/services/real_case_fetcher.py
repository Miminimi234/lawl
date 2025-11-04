"""
Real Case Fetcher - Uses OpenAI to get ACTUAL recent court cases
OpenAI has knowledge of real Supreme Court and Circuit Court cases from 2023-2024
"""
import os
from typing import List, Dict
from openai import OpenAI

class RealCaseFetcher:
    """Fetch information about REAL recent court cases using OpenAI's knowledge"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def get_real_cases(self, count: int = 20) -> List[Dict]:
        """Get real recent court cases from OpenAI's knowledge"""
        
        prompt = f"""List {count} REAL recent United States Supreme Court and Federal Circuit Court cases from 2023-2024.

For each case, provide:
1. Full case name (Plaintiff v. Defendant format)
2. Citation (e.g., "597 U.S. ___ (2023)" or "F.4th")  
3. Court name
4. Case type (contract, employment, civil_rights, criminal, etc.)
5. Brief summary (2-3 sentences about what the case was about)
6. Year decided

Format each as:
CASE {{number}}
Title: {{name}}
Citation: {{citation}}
Court: {{court}}
Type: {{type}}
Year: {{year}}
Summary: {{summary}}

---

Give me REAL cases that actually exist. Include landmark cases like Students for Fair Admissions v. Harvard, Biden v. Nebraska, Andy Warhol Foundation v. Goldsmith, etc."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.3,
                max_tokens=3000
            )
            
            text = response.choices[0].message.content
            
            # Parse the response
            cases = []
            current_case = {}
            
            for line in text.split('\n'):
                line = line.strip()
                
                if line.startswith('CASE '):
                    if current_case:
                        cases.append(current_case)
                    current_case = {}
                elif line.startswith('Title:'):
                    current_case['title'] = line.replace('Title:', '').strip()
                elif line.startswith('Citation:'):
                    current_case['citation'] = line.replace('Citation:', '').strip()
                elif line.startswith('Court:'):
                    current_case['court'] = line.replace('Court:', '').strip()
                elif line.startswith('Type:'):
                    current_case['case_type'] = line.replace('Type:', '').strip()
                elif line.startswith('Year:'):
                    current_case['year'] = line.replace('Year:', '').strip()
                elif line.startswith('Summary:'):
                    current_case['summary'] = line.replace('Summary:', '').strip()
                elif line and current_case.get('summary'):
                    # Continue multi-line summary
                    current_case['summary'] += ' ' + line
            
            # Add last case
            if current_case:
                cases.append(current_case)
            
            # Set jurisdiction based on court
            for case in cases:
                court = case.get('court', '')
                if 'Supreme Court' in court:
                    case['jurisdiction'] = 'U.S. Supreme Court'
                elif 'Circuit' in court:
                    case['jurisdiction'] = court
                else:
                    case['jurisdiction'] = 'Federal Court'
            
            return cases
            
        except Exception as e:
            print(f"Error fetching real cases: {e}")
            return []
