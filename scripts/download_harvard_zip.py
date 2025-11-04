#!/usr/bin/env python3
"""
Download 250-500 REAL cases from Harvard CAP by downloading volume ZIPs
Downloads from https://static.case.law/ - NO API NEEDED!
"""
import requests
import zipfile
import json
import os
import random
import time
from pathlib import Path
from io import BytesIO

# Configuration
STATIC_BASE = "https://static.case.law"
OUTPUT_DIR = Path("data/processed/harvard_cases")
TARGET_CASES = 1500  # Increased from 500 to get more cases
MAX_CASES_PER_VOLUME = 50  # Limit per volume to ensure variety

# Mix of reporters and their recent volumes (more recent = more relevant)
VOLUME_SELECTIONS = [
    # U.S. Supreme Court (volumes 540-572 are 1990s-2020s)
    ('us', list(range(500, 573))),
    
    # Federal circuits (expanded range)
    ('f3d', list(range(700, 1000))),
    ('f2d', list(range(900, 1000))),
    
    # California Supreme Court
    ('cal-4th', list(range(1, 75))),
    ('cal-3d', list(range(1, 63))),
    ('cal-2d', list(range(50, 70))),
    ('cal', list(range(50, 70))),
    ('cal-app-4th', list(range(100, 200))),
    
    # New York
    ('ny', list(range(50, 110))),
    ('ny-2d', list(range(50, 110))),
    
    # Texas
    ('sw3d', list(range(400, 650))),
    ('tex', list(range(800, 1000))),
    
    # Pennsylvania
    ('pa', list(range(500, 650))),
    ('a2d', list(range(800, 1200))),
    
    # State reporters (expanded)
    ('ill-2d', list(range(200, 380))),
    ('ne3d', list(range(1, 200))),
    ('mass', list(range(400, 490))),
    ('ohio', list(range(100, 180))),
    ('fla', list(range(800, 1100))),
    ('so3d', list(range(1, 350))),
    ('mich', list(range(400, 510))),
    ('nw2d', list(range(700, 950))),
    ('wash-2d', list(range(100, 200))),
    ('se2d', list(range(600, 850))),
]


def download_and_extract_volume(reporter, volume_num):
    """Download a volume ZIP and extract all case JSONs"""
    url = f"{STATIC_BASE}/{reporter}/{volume_num}.zip"
    
    print(f"   📦 Downloading {reporter}/{volume_num}.zip...")
    
    try:
        resp = requests.get(url, timeout=60)
        
        if resp.status_code != 200:
            print(f"      ⚠️  HTTP {resp.status_code}")
            return []
        
        # Download size check
        size_mb = len(resp.content) / (1024 * 1024)
        print(f"      📊 {size_mb:.1f}MB")
        
        # Extract ZIP in memory
        cases = []
        
        with zipfile.ZipFile(BytesIO(resp.content)) as zf:
            # Find all JSON files in the ZIP
            json_files = [f for f in zf.namelist() if f.endswith('.json')]
            
            if not json_files:
                print(f"      ⚠️  No JSON files found")
                return []
            
            # Limit to avoid huge volumes
            random.shuffle(json_files)
            json_files = json_files[:MAX_CASES_PER_VOLUME]
            
            for json_file in json_files:
                try:
                    with zf.open(json_file) as f:
                        case_data = json.load(f)
                        
                        # Handle both single case objects and lists of cases
                        if isinstance(case_data, list):
                            for single_case in case_data:
                                cases.append({
                                    'data': single_case,
                                    'reporter': reporter,
                                    'volume': volume_num,
                                    'source_file': json_file
                                })
                        else:
                            cases.append({
                                'data': case_data,
                                'reporter': reporter,
                                'volume': volume_num,
                                'source_file': json_file
                            })
                except Exception as e:
                    continue
        
        print(f"      ✅ Extracted {len(cases)} cases")
        return cases
        
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return []


def main():
    print("\n" + "="*80)
    print("📡 HARVARD CAP - BULK CASE DOWNLOADER")
    print("="*80)
    print(f"\n   Source: {STATIC_BASE}")
    print(f"   Target: {TARGET_CASES} REAL cases")
    print(f"   Method: Download volume ZIPs")
    print(f"   Output: {OUTPUT_DIR}\n")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check existing
    existing = list(OUTPUT_DIR.glob("*.json"))
    existing_count = len(existing)
    if existing:
        print(f"📂 Found {existing_count} existing cases")
        if existing_count >= TARGET_CASES:
            print(f"✅ Already have {existing_count} cases (target: {TARGET_CASES})!")
            print(f"   To download more, increase TARGET_CASES in the script.\n")
            return 0
        else:
            print(f"   Need {TARGET_CASES - existing_count} more cases to reach target\n")
    
    all_cases = []
    
    print("🔍 Downloading volumes...\n")
    
    # Shuffle for randomness
    random.shuffle(VOLUME_SELECTIONS)
    
    for reporter, volumes in VOLUME_SELECTIONS:
        if len(all_cases) >= TARGET_CASES:
            break
        
        print(f"📚 {reporter.upper()}")
        
        # Pick random volumes from this reporter
        random.shuffle(volumes)
        
        for volume_num in volumes[:5]:  # Max 5 volumes per reporter (increased from 3)
            if len(all_cases) >= TARGET_CASES:
                break
            
            cases = download_and_extract_volume(reporter, volume_num)
            all_cases.extend(cases)
            
            print(f"      📊 Total: {len(all_cases)}/{TARGET_CASES}")
            
            # Rate limiting
            time.sleep(1)
        
        print()
    
    # Shuffle all cases for variety
    random.shuffle(all_cases)
    
    # Save first TARGET_CASES
    print(f"\n💾 Saving {min(len(all_cases), TARGET_CASES)} cases...\n")
    
    saved = 0
    for i, case_info in enumerate(all_cases[:TARGET_CASES], 1):
        try:
            case_data = case_info['data']
            reporter = case_info['reporter']
            volume = case_info['volume']
            
            # Skip if case_data is not a dict
            if not isinstance(case_data, dict):
                continue
            
            # Extract case info
            case_id = case_data.get('id') or f"{reporter}_{volume}_{i}"
            case_name = case_data.get('name_abbreviation') or case_data.get('name') or f"case_{i}"
            
            # Clean filename
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in str(case_name))
            safe_name = safe_name[:80]
            
            filename = OUTPUT_DIR / f"{case_id}_{reporter}_{safe_name}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(case_data, f, indent=2)
            
            saved += 1
            
            if saved <= 10 or saved % 100 == 0:
                print(f"   [{saved}/{min(len(all_cases), TARGET_CASES)}] {str(case_name)[:60]}")
        except Exception as e:
            continue
    
    total_size_mb = sum(f.stat().st_size for f in OUTPUT_DIR.glob('*.json')) / (1024*1024)
    
    print("\n" + "="*80)
    print("✅ DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\n   ✅ Saved: {saved} REAL cases")
    print(f"   📁 Location: {OUTPUT_DIR}")
    print(f"   💾 Total size: {total_size_mb:.1f}MB")
    print(f"   📊 Average: {total_size_mb/saved:.2f}MB per case")
    
    # Sample case info
    sample_file = list(OUTPUT_DIR.glob('*.json'))[0]
    with open(sample_file) as f:
        sample = json.load(f)
    
    print(f"\n   📄 Sample case:")
    print(f"      Title: {sample.get('name') or sample.get('name_abbreviation')}")
    print(f"      Court: {sample.get('court', {}).get('name') if isinstance(sample.get('court'), dict) else sample.get('court')}")
    print(f"      Date: {sample.get('decision_date')}")
    
    print(f"\n   Next: Run standalone server to load these cases")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

