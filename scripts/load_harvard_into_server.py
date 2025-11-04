#!/usr/bin/env python3
"""
Load downloaded Harvard CAP cases into VERDICT format
Converts Harvard JSON to our simplified case structure
"""
import json
import random
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path("data/processed/harvard_cases")
OUTPUT_FILE = Path("data/verdict_cases.json")


def convert_harvard_case(harvard_case, case_id):
    """Convert Harvard CAP case format to VERDICT format"""
    
    # Extract basic info
    name = harvard_case.get('name_abbreviation') or harvard_case.get('name') or f"Case {case_id}"
    
    # Court info
    court_data = harvard_case.get('court', {})
    if isinstance(court_data, dict):
        court = court_data.get('name') or 'Unknown Court'
    else:
        court = str(court_data) if court_data else 'Unknown Court'
    
    # Citation
    citations = harvard_case.get('citations', [])
    citation = citations[0].get('cite') if citations and isinstance(citations, list) else harvard_case.get('citation') or 'No citation'
    
    # Decision date
    decision_date = harvard_case.get('decision_date') or datetime.now().strftime('%Y-%m-%d')
    
    # Case text - extract from opinions
    casebody = harvard_case.get('casebody', {})
    case_text = ""
    
    if isinstance(casebody, dict):
        opinions = casebody.get('opinions', [])
        if opinions and isinstance(opinions, list):
            # Combine all opinion texts
            opinion_texts = []
            for opinion in opinions:
                if isinstance(opinion, dict):
                    text = opinion.get('text', '')
                    author = opinion.get('author', '')
                    opinion_type = opinion.get('type', '')
                    
                    if text:
                        header = f"\n{'='*60}\n"
                        if author or opinion_type:
                            header += f"{opinion_type.upper() if opinion_type else 'OPINION'}"
                            if author:
                                header += f" by {author}"
                            header += f"\n{'='*60}\n\n"
                        opinion_texts.append(header + text)
            
            case_text = "\n\n".join(opinion_texts)
    
    # Fallback if no text found
    if not case_text or len(case_text.strip()) < 50:
        case_text = f"Court opinion for {name}.\n\nCitation: {citation}\nCourt: {court}\nDate: {decision_date}\n\n[Full text not available in extracted data]"
    
    # No truncation - include full opinion text!
    
    # Determine case type from case name/text
    case_type = determine_case_type(name, case_text)
    
    # Generate case number
    year = decision_date[:4] if decision_date else '2024'
    case_number = f"{year}-CV-{str(case_id).zfill(5)}"
    
    return {
        'id': case_id,
        'title': name,
        'case_number': case_number,
        'case_type': case_type,
        'jurisdiction': court,
        'citation': citation,
        'decision_date': decision_date,
        'case_text': case_text,
        'status': 'completed',
        'url': harvard_case.get('frontend_url') or harvard_case.get('url') or '',
        'snippet': case_text[:200] + '...' if len(case_text) > 200 else case_text,
        'confidence': 1.0,  # Real cases have 100% confidence
    }


def determine_case_type(name, text):
    """Determine legal area from case name and text"""
    name_lower = name.lower()
    text_lower = text.lower()
    combined = name_lower + ' ' + text_lower[:500]
    
    if any(keyword in combined for keyword in ['contract', 'breach', 'agreement', 'covenant']):
        return 'Contract Law'
    elif any(keyword in combined for keyword in ['employment', 'discrimination', 'title vii', 'workplace', 'labor']):
        return 'Employment Law'
    elif any(keyword in combined for keyword in ['criminal', 'prosecution', 'defendant', 'sentence', 'conviction']):
        return 'Criminal Law'
    elif any(keyword in combined for keyword in ['civil rights', '1983', 'constitutional', 'amendment', 'freedom']):
        return 'Civil Rights'
    elif any(keyword in combined for keyword in ['property', 'real estate', 'land', 'deed', 'title']):
        return 'Property Law'
    elif any(keyword in combined for keyword in ['tort', 'negligence', 'liability', 'injury', 'damages']):
        return 'Tort Law'
    elif any(keyword in combined for keyword in ['tax', 'irs', 'revenue', 'taxable']):
        return 'Tax Law'
    elif any(keyword in combined for keyword in ['family', 'divorce', 'custody', 'marriage']):
        return 'Family Law'
    elif any(keyword in combined for keyword in ['appeal', 'appellate', 'affirm', 'reverse']):
        return 'Appellate'
    else:
        return 'General Civil'


def main():
    print("\n" + "="*80)
    print("📚 LOADING HARVARD CASES INTO VERDICT")
    print("="*80)
    
    # Find all case files
    case_files = list(INPUT_DIR.glob("*.json"))
    
    if not case_files:
        print(f"\n❌ No case files found in {INPUT_DIR}")
        print("   Run: python3 scripts/download_harvard_zip.py first\n")
        return 1
    
    print(f"\n📂 Found {len(case_files)} case files")
    print(f"🔄 Converting to VERDICT format...\n")
    
    verdict_cases = []
    
    for i, case_file in enumerate(case_files, 1):
        try:
            with open(case_file) as f:
                harvard_case = json.load(f)
            
            verdict_case = convert_harvard_case(harvard_case, i)
            verdict_cases.append(verdict_case)
            
            if i <= 10 or i % 100 == 0:
                print(f"   [{i}/{len(case_files)}] {verdict_case['title'][:60]}")
                
        except Exception as e:
            print(f"   ⚠️  Error loading {case_file.name}: {e}")
            continue
    
    # Shuffle for variety
    random.shuffle(verdict_cases)
    
    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(verdict_cases, f, indent=2)
    
    # Stats
    case_types = {}
    for case in verdict_cases:
        ct = case['case_type']
        case_types[ct] = case_types.get(ct, 0) + 1
    
    print("\n" + "="*80)
    print("✅ CONVERSION COMPLETE")
    print("="*80)
    print(f"\n   ✅ Converted: {len(verdict_cases)} cases")
    print(f"   💾 Saved to: {OUTPUT_FILE}")
    print(f"   📊 Size: {OUTPUT_FILE.stat().st_size / (1024*1024):.1f}MB")
    
    print(f"\n   📊 Case Types:")
    for ct, count in sorted(case_types.items(), key=lambda x: x[1], reverse=True):
        print(f"      {ct}: {count}")
    
    # Sample
    sample = verdict_cases[0]
    print(f"\n   📄 Sample case:")
    print(f"      Title: {sample['title']}")
    print(f"      Type: {sample['case_type']}")
    print(f"      Court: {sample['jurisdiction']}")
    print(f"      Date: {sample['decision_date']}")
    print(f"      Citation: {sample['citation']}")
    
    print(f"\n   Next: Restart standalone server to see these REAL cases!")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

