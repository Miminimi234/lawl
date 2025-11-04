#!/usr/bin/env python3
"""
Download 250-500 REAL individual cases from Harvard CAP
Mixes different years, jurisdictions, and case types
Each case is a separate JSON file < 1MB
"""
import requests
import time
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
OUTPUT_DIR = Path("data/processed/harvard_individual")
TARGET_CASES = 500
MAX_SIZE_MB = 1.0

# Harvard CAP API
BASE_URL = "https://api.case.law/v1"

# Mix of jurisdictions (state abbreviations)
JURISDICTIONS = [
    'ill',  # Illinois
    'cal',  # California
    'ny',   # New York
    'mass', # Massachusetts
    'tex',  # Texas
    'fla',  # Florida
    'pa',   # Pennsylvania
    'ohio', # Ohio
    'mich', # Michigan
    'nc'    # North Carolina
]

# Years to sample from
YEARS = list(range(2010, 2024))

def fetch_cases_for_jurisdiction_year(jurisdiction, year, limit=10):
    """Fetch cases for a specific jurisdiction and year"""
    url = f"{BASE_URL}/cases/"
    
    params = {
        'jurisdiction': jurisdiction,
        'decision_date_min': f'{year}-01-01',
        'decision_date_max': f'{year}-12-31',
        'page_size': limit,
        'full_case': 'true'  # Get full case data
    }
    
    headers = {
        'User-Agent': 'VerdictLegalAI/1.0'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            return results
        else:
            print(f"   ⚠️  HTTP {response.status_code} for {jurisdiction} {year}")
            return []
            
    except Exception as e:
        print(f"   ⚠️  Error {jurisdiction} {year}: {e}")
        return []


def estimate_size(case_data):
    """Estimate size of case in MB"""
    json_str = json.dumps(case_data)
    size_mb = len(json_str.encode('utf-8')) / (1024 * 1024)
    return size_mb


def main():
    print("\n" + "="*80)
    print("📡 HARVARD CAP - DOWNLOADING REAL CASES")
    print("="*80)
    print(f"\n   Target: {TARGET_CASES} cases")
    print(f"   Max size: {MAX_SIZE_MB}MB per case")
    print(f"   Jurisdictions: {len(JURISDICTIONS)}")
    print(f"   Year range: {min(YEARS)}-{max(YEARS)}")
    print(f"   Output: {OUTPUT_DIR}\n")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    skipped_size = 0
    skipped_duplicate = 0
    errors = 0
    
    # Shuffle for variety
    random.shuffle(JURISDICTIONS)
    random.shuffle(YEARS)
    
    # Track seen case IDs
    seen_ids = set()
    
    # Load existing cases
    existing_files = list(OUTPUT_DIR.glob("*.json"))
    if existing_files:
        print(f"📂 Found {len(existing_files)} existing cases, continuing...\n")
        for f in existing_files:
            try:
                with open(f) as file:
                    case = json.load(file)
                    seen_ids.add(str(case.get('id', '')))
                    downloaded += 1
            except:
                pass
    
    print("🔍 Fetching cases...\n")
    
    # Download cases from mix of jurisdictions and years
    attempts = 0
    max_attempts = TARGET_CASES * 3  # Try up to 3x target to account for skips
    
    while downloaded < TARGET_CASES and attempts < max_attempts:
        jurisdiction = random.choice(JURISDICTIONS)
        year = random.choice(YEARS)
        
        print(f"   [{downloaded}/{TARGET_CASES}] Fetching {jurisdiction.upper()} {year}...")
        
        cases = fetch_cases_for_jurisdiction_year(jurisdiction, year, limit=5)
        attempts += 1
        
        for case in cases:
            if downloaded >= TARGET_CASES:
                break
            
            case_id = str(case.get('id', ''))
            
            # Skip duplicates
            if case_id in seen_ids:
                skipped_duplicate += 1
                continue
            
            # Check size
            size_mb = estimate_size(case)
            if size_mb > MAX_SIZE_MB:
                skipped_size += 1
                continue
            
            # Save case
            case_name = case.get('name_abbreviation') or case.get('name') or f"case_{case_id}"
            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in case_name)
            safe_name = safe_name[:100]  # Limit length
            
            filename = OUTPUT_DIR / f"{case_id}_{safe_name}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(case, f, indent=2)
            
            seen_ids.add(case_id)
            downloaded += 1
            
            if downloaded <= 10 or downloaded % 50 == 0:
                print(f"      ✅ {case_name[:60]} ({size_mb:.2f}MB)")
        
        # Rate limiting
        time.sleep(0.5)
        
        # Progress update
        if attempts % 10 == 0:
            print(f"\n   📊 Progress: {downloaded}/{TARGET_CASES} cases ({attempts} API calls)\n")
    
    print("\n" + "="*80)
    print("✅ DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\n   ✅ Downloaded: {downloaded} real cases")
    print(f"   ⏭️  Skipped (size): {skipped_size}")
    print(f"   ⏭️  Skipped (duplicate): {skipped_duplicate}")
    print(f"   ❌ Errors: {errors}")
    print(f"   📁 Location: {OUTPUT_DIR}")
    print(f"\n   Total size: {sum(f.stat().st_size for f in OUTPUT_DIR.glob('*.json')) / (1024*1024):.1f}MB")
    print(f"\n   Next: python3 scripts/load_harvard_cases.py")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

