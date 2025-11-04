#!/usr/bin/env python3
"""
Bulk Data ETL Pipeline
Extracts downloaded case law archives and ingests into local SQLite DB
"""
import os
import glob
import json
import hashlib
import time
import sys
from pathlib import Path

# Add util to path
sys.path.insert(0, str(Path(__file__).parent))

from util.io import ensure_dirs, list_artifacts, extract_if_archive, get_db, init_schema_sqlite, get_db_stats

# Configuration from environment
RAW_DIR = os.getenv("RAW_DIR", "data/raw")
PROC_DIR = os.getenv("PROC_DIR", "data/processed")
DB_KIND = os.getenv("DB_KIND", "sqlite")
DB_PATH_SQLITE = os.getenv("DB_PATH_SQLITE", "data/caselaw.db")
DB_PATH_DUCKDB = os.getenv("DB_PATH_DUCKDB", "data/caselaw.duckdb")

def main():
    print("\n" + "="*70)
    print("⚙️  VERDICT BULK DATA ETL PIPELINE")
    print("="*70)
    print("")
    
    # Ensure directories exist
    ensure_dirs(RAW_DIR, PROC_DIR, "data/cache")
    
    # Step 1: Extract all archives
    print("📦 STEP 1: Extracting archives")
    print("-" * 70)
    
    artifacts = list_artifacts(RAW_DIR)
    if not artifacts:
        print("⚠️  No files found in", RAW_DIR)
        print("   Run 'make bulk' first to download data")
        return 1
    
    extracted_count = 0
    for art in artifacts:
        if extract_if_archive(art, PROC_DIR):
            extracted_count += 1
    
    print(f"\n✅ Extracted {extracted_count} archive(s)\n")
    
    # Step 2: Initialize database
    print("📊 STEP 2: Initializing database")
    print("-" * 70)
    
    con, kind = get_db(DB_KIND, DB_PATH_SQLITE, DB_PATH_DUCKDB)
    print(f"Using {kind.upper()}: {DB_PATH_SQLITE if kind == 'sqlite' else DB_PATH_DUCKDB}")
    
    if kind == "sqlite":
        init_schema_sqlite(con)
    
    # Step 3: Ingest JSON/JSONL files
    print("\n📥 STEP 3: Ingesting case data")
    print("-" * 70)
    
    if kind == "sqlite":
        ingest_sqlite(con, PROC_DIR)
    else:
        print("⚠️  DuckDB ingestion not yet implemented")
    
    # Step 4: Report statistics
    print("\n📊 STEP 4: Database statistics")
    print("-" * 70)
    
    stats = get_db_stats(con, kind)
    print(f"\n   Total cases: {stats['total_cases']:,}")
    
    if stats['top_courts']:
        print(f"\n   Top courts:")
        for court, count in stats['top_courts']:
            print(f"   - {court}: {count:,} cases")
    
    if stats['date_range'][0]:
        print(f"\n   Date range: {stats['date_range'][0]} to {stats['date_range'][1]}")
    
    con.close()
    
    print("\n" + "="*70)
    print("✅ ETL COMPLETE")
    print("="*70)
    print(f"\n   Database: {DB_PATH_SQLITE if kind == 'sqlite' else DB_PATH_DUCKDB}")
    print(f"   Total cases: {stats['total_cases']:,}")
    print(f"\n   Next: make query  # Run sample queries")
    print(f"         make verify # View statistics\n")
    
    return 0


def iter_json_records(path):
    """Iterate over JSON records (handles .json and .jsonl)"""
    try:
        if path.endswith(".jsonl"):
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as e:
                            if line_num <= 5:  # Only warn for first few
                                print(f"   ⚠️  JSON error line {line_num}: {e}")
        
        elif path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    obj = json.load(f)
                    if isinstance(obj, list):
                        for rec in obj:
                            yield rec
                    elif isinstance(obj, dict):
                        # Check if it's a wrapper with results
                        if "results" in obj and isinstance(obj["results"], list):
                            for rec in obj["results"]:
                                yield rec
                        else:
                            yield obj
                except json.JSONDecodeError as e:
                    print(f"   ⚠️  JSON error in {path}: {e}")
    
    except Exception as e:
        print(f"   ⚠️  Error reading {path}: {e}")


def normalize(rec, raw_path):
    """
    Normalize case record from various formats (Harvard CAP, CourtListener, etc.)
    
    Returns tuple: (id, court, citation, date, title, jurisdiction, reporter, case_type, raw_path, full_text_available)
    """
    # ID
    id_ = str(rec.get("id") or 
              rec.get("case_id") or 
              rec.get("uuid") or 
              rec.get("cluster_id") or
              hashlib.md5(json.dumps(rec, sort_keys=True).encode()).hexdigest())
    
    # Court (handle nested objects)
    court = rec.get("court")
    if isinstance(court, dict):
        court = court.get("name") or court.get("slug") or str(court)
    court = str(court) if court else None
    
    # Citation (handle arrays)
    citation = rec.get("citation") or rec.get("case_name_full")
    if not citation and rec.get("citations"):
        cites = rec.get("citations")
        if isinstance(cites, list) and cites:
            citation = cites[0].get("cite") if isinstance(cites[0], dict) else str(cites[0])
    citation = str(citation) if citation else None
    
    # Date
    date = rec.get("decision_date") or rec.get("date") or rec.get("date_filed") or rec.get("date_created")
    date = str(date) if date else None
    
    # Title/Name
    title = rec.get("name") or rec.get("title") or rec.get("case_name") or rec.get("case_name_short")
    title = str(title) if title else None
    
    # Jurisdiction (handle nested)
    jurisdiction = rec.get("jurisdiction")
    if isinstance(jurisdiction, dict):
        jurisdiction = jurisdiction.get("name") or jurisdiction.get("slug") or str(jurisdiction)
    jurisdiction = str(jurisdiction) if jurisdiction else None
    
    # Reporter
    reporter = rec.get("reporter") or rec.get("volume")
    reporter = str(reporter) if reporter else None
    
    # Case type (try to infer)
    case_type = rec.get("type") or rec.get("case_type")
    if not case_type and title:
        title_lower = title.lower()
        if any(w in title_lower for w in ['criminal', 'people v', 'state v', 'commonwealth v']):
            case_type = 'criminal'
        elif any(w in title_lower for w in ['contract', 'breach']):
            case_type = 'contract'
        elif any(w in title_lower for w in ['employ', 'discriminat']):
            case_type = 'employment'
    case_type = str(case_type) if case_type else 'general'
    
    # Check if full text available
    full_text_available = 1 if (rec.get("casebody") or rec.get("plain_text") or rec.get("html") or rec.get("text")) else 0
    
    return (id_, court, citation, date, title, jurisdiction, reporter, case_type, raw_path, full_text_available)


def ingest_sqlite(con, proc_dir):
    """Ingest all JSON/JSONL files from processed directory into SQLite"""
    cur = con.cursor()
    
    # Enable WAL mode for better performance
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")
    
    # Find all JSON files
    patterns = [
        os.path.join(proc_dir, "**/*.json"),
        os.path.join(proc_dir, "**/*.jsonl"),
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    
    if not files:
        print("⚠️  No JSON/JSONL files found in", proc_dir)
        return 0
    
    print(f"   Found {len(files)} JSON/JSONL file(s)")
    print(f"   Processing...")
    
    inserted = 0
    skipped = 0
    errors = 0
    
    start_time = time.time()
    
    for i, path in enumerate(files, 1):
        file_inserted = 0
        
        for rec in iter_json_records(path):
            try:
                row = normalize(rec, path)
                cur.execute("""
                    INSERT OR IGNORE INTO cases
                    (id, court, citation, decision_date, title, jurisdiction, reporter, case_type, raw_path, full_text_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
                
                if cur.rowcount > 0:
                    file_inserted += 1
                    inserted += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                errors += 1
                if errors <= 5:  # Only show first few errors
                    print(f"   ⚠️  Error on record: {e}")
        
        if file_inserted > 0 and i <= 10:  # Show progress for first 10 files
            print(f"   [{i}/{len(files)}] {os.path.basename(path)}: +{file_inserted} cases")
        
        # Commit periodically
        if i % 10 == 0:
            con.commit()
    
    # Final commit
    con.commit()
    
    elapsed = time.time() - start_time
    
    print(f"\n   ✅ Inserted: {inserted:,} cases")
    print(f"   ⏭️  Skipped: {skipped:,} (duplicates)")
    if errors > 0:
        print(f"   ⚠️  Errors: {errors}")
    print(f"   ⏱️  Time: {elapsed:.1f}s")
    
    return inserted


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code if exit_code else 0)

