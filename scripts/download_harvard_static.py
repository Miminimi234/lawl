#!/usr/bin/env python3
"""
Download 250-500 REAL individual cases from Harvard CAP static hosting
Downloads directly from https://static.case.law/ - NO API NEEDED!
Mixes different reporters, years, and jurisdictions
"""
import requests
import json
import os
import random
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
STATIC_BASE = "https://static.case.law"
OUTPUT_DIR = Path("data/processed/harvard_static")
TARGET_CASES = 500
MAX_WORKERS = 5  # Parallel downloads

# Mix of interesting reporters for variety
REPORTERS = [
    'us',          # U.S. Supreme Court
    'f3d',         # Federal 3rd series
    'f-supp-3d',   # Federal Supplement
    'cal',         # California
    'cal-4th',     # California 4th series
    'ny',          # New York
    'ill',         # Illinois
    'ill-2d',      # Illinois 2nd series
    'mass',        # Massachusetts
    'tex',         # Texas
    'pa',          # Pennsylvania
    'ohio',        # Ohio
    'fla',         # Florida
    'wash-2d',     # Washington 2nd
    'mich',        # Michigan
    'sw3d',        # South Western 3rd
    'ne3d',        # North Eastern 3rd
    'se2d',        # South Eastern 2nd
    'nw2d',        # North Western 2nd
    'so3d',        # Southern 3rd
]

def download_metadata():
    """Download reporter metadata to understand structure"""
    print("📋 Downloading metadata...")
    
    try:
        # Download reporters metadata
        resp = requests.get(f"{STATIC_BASE}/ReportersMetadata.json", timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"   ⚠️  Metadata error: {e}")
    
    return {}


def list_reporter_contents(reporter):
    """List available volumes for a reporter"""
    url = f"{STATIC_BASE}/{reporter}/"
    
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            # Parse HTML directory listing
            text = resp.text
            
            # Extract folder names (volumes)
            import re
            volumes = re.findall(r'<a href="([^"]+)/">', text)
            volumes = [v for v in volumes if v != '..']
            return volumes
    except Exception as e:
        pass
    
    return []


def download_case_file(reporter, volume, filename):
    """Download a single case file"""
    url = f"{STATIC_BASE}/{reporter}/{volume}/{filename}"
    
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            
            # Check size
            size_mb = len(resp.content) / (1024 * 1024)
            if size_mb <= 1.0:  # Only cases < 1MB
                return data, size_mb
    except:
        pass
    
    return None, 0


def download_random_cases_from_reporter(reporter, target_count=25):
    """Download random cases from a reporter"""
    cases = []
    
    print(f"   📚 {reporter.upper()}...")
    
    # List available volumes
    volumes = list_reporter_contents(reporter)
    if not volumes:
        print(f"      ⚠️  No volumes found")
        return cases
    
    # Shuffle for randomness
    random.shuffle(volumes)
    
    # Try to get cases from random volumes
    for volume in volumes[:10]:  # Try up to 10 volumes
        if len(cases) >= target_count:
            break
        
        # List files in volume
        vol_url = f"{STATIC_BASE}/{reporter}/{volume}/"
        
        try:
            resp = requests.get(vol_url, timeout=10)
            if resp.status_code == 200:
                import re
                files = re.findall(r'<a href="([^"]+\.json)">', resp.text)
                
                if files:
                    # Pick random files from this volume
                    random.shuffle(files)
                    
                    for filename in files[:5]:  # Max 5 per volume
                        if len(cases) >= target_count:
                            break
                        
                        data, size_mb = download_case_file(reporter, volume, filename)
                        
                        if data:
                            cases.append({
                                'data': data,
                                'reporter': reporter,
                                'volume': volume,
                                'filename': filename,
                                'size_mb': size_mb
                            })
                        
                        time.sleep(0.1)  # Rate limiting
        except:
            continue
    
    print(f"      ✅ Got {len(cases)} cases")
    return cases


def main():
    print("\n" + "="*80)
    print("📡 HARVARD CAP STATIC FILE DOWNLOADER")
    print("="*80)
    print(f"\n   Source: https://static.case.law/")
    print(f"   Target: {TARGET_CASES} REAL cases")
    print(f"   Max size: 1MB per case")
    print(f"   Reporters: {len(REPORTERS)} different sources")
    print(f"   Output: {OUTPUT_DIR}\n")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check existing
    existing = list(OUTPUT_DIR.glob("*.json"))
    if existing:
        print(f"📂 Found {len(existing)} existing cases\n")
        if len(existing) >= TARGET_CASES:
            print(f"✅ Already have {len(existing)} cases! Skipping download.\n")
            return 0
    
    all_cases = []
    per_reporter = TARGET_CASES // len(REPORTERS) + 5  # ~25-30 per reporter
    
    print(f"🔍 Downloading {per_reporter} cases per reporter...\n")
    
    # Shuffle reporters for variety
    random.shuffle(REPORTERS)
    
    # Download from each reporter
    for reporter in REPORTERS:
        if len(all_cases) >= TARGET_CASES:
            break
        
        cases = download_random_cases_from_reporter(reporter, target_count=per_reporter)
        all_cases.extend(cases)
        
        print(f"   📊 Total so far: {len(all_cases)}/{TARGET_CASES}\n")
        
        # Don't overdo it
        if len(all_cases) >= TARGET_CASES * 1.2:
            break
    
    # Save all cases
    print(f"\n💾 Saving {len(all_cases)} cases to disk...\n")
    
    saved = 0
    for i, case_info in enumerate(all_cases[:TARGET_CASES], 1):
        case_data = case_info['data']
        reporter = case_info['reporter']
        
        # Generate filename
        case_id = case_data.get('id') or f"{reporter}_{i}"
        case_name = case_data.get('name_abbreviation') or case_data.get('name') or f"case_{i}"
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in case_name)
        safe_name = safe_name[:80]
        
        filename = OUTPUT_DIR / f"{case_id}_{reporter}_{safe_name}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2)
        
        saved += 1
        
        if saved <= 10 or saved % 100 == 0:
            print(f"   [{saved}/{min(len(all_cases), TARGET_CASES)}] {case_name[:60]}")
    
    total_size_mb = sum(f.stat().st_size for f in OUTPUT_DIR.glob('*.json')) / (1024*1024)
    
    print("\n" + "="*80)
    print("✅ DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\n   ✅ Saved: {saved} REAL cases")
    print(f"   📁 Location: {OUTPUT_DIR}")
    print(f"   💾 Total size: {total_size_mb:.1f}MB")
    print(f"   📊 Average: {total_size_mb/saved:.2f}MB per case")
    print(f"\n   Next: python3 scripts/load_harvard_cases.py")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

