#!/usr/bin/env python3
"""
Local Query Tool - Query case law database offline
Works completely offline after initial data download
"""
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.getenv("DB_PATH_SQLITE", "data/caselaw.db")

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        print(f"   Run 'make bulk && make etl' first")
        return 1
    
    print("\n" + "="*70)
    print("🔍 VERDICT LOCAL CASE LAW QUERY")
    print("="*70)
    print(f"\nDatabase: {DB_PATH}")
    print("Mode: OFFLINE (no network required)\n")
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Total cases
        total = cur.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        print(f"📊 Total Cases: {total:,}\n")
        
        if total == 0:
            print("⚠️  No cases in database. Run 'make etl' to ingest data.")
            return 1
        
        # Top courts
        print("🏛️  TOP 10 COURTS:")
        print("-" * 70)
        for row in cur.execute("""
            SELECT court, COUNT(*) as cnt 
            FROM cases 
            WHERE court IS NOT NULL
            GROUP BY court 
            ORDER BY cnt DESC 
            LIMIT 10
        """):
            print(f"   {row['court'][:50]:50s} {row['cnt']:>10,} cases")
        
        # Date range
        print(f"\n📅 DATE RANGE:")
        print("-" * 70)
        date_row = cur.execute("""
            SELECT MIN(decision_date) as min_date, MAX(decision_date) as max_date 
            FROM cases 
            WHERE decision_date IS NOT NULL
        """).fetchone()
        print(f"   Earliest: {date_row['min_date']}")
        print(f"   Latest:   {date_row['max_date']}")
        
        # Sample recent cases
        print(f"\n📰 SAMPLE RECENT CASES:")
        print("-" * 70)
        for i, row in enumerate(cur.execute("""
            SELECT title, citation, court, decision_date
            FROM cases 
            WHERE title IS NOT NULL AND decision_date IS NOT NULL
            ORDER BY decision_date DESC
            LIMIT 5
        """), 1):
            print(f"\n{i}. {row['title'][:60]}")
            print(f"   {row['citation'] or 'N/A'} | {row['court']}")
            print(f"   {row['decision_date']}")
        
        # Case types
        print(f"\n⚖️  CASE TYPES:")
        print("-" * 70)
        for row in cur.execute("""
            SELECT case_type, COUNT(*) as cnt
            FROM cases
            GROUP BY case_type
            ORDER BY cnt DESC
            LIMIT 10
        """):
            print(f"   {row['case_type']:20s} {row['cnt']:>10,} cases")
        
        # Full text availability
        print(f"\n📄 FULL TEXT AVAILABILITY:")
        print("-" * 70)
        full_text_row = cur.execute("""
            SELECT 
                SUM(CASE WHEN full_text_available = 1 THEN 1 ELSE 0 END) as with_text,
                SUM(CASE WHEN full_text_available = 0 THEN 1 ELSE 0 END) as without_text
            FROM cases
        """).fetchone()
        print(f"   With full text:    {full_text_row[0]:>10,} cases")
        print(f"   Without full text: {full_text_row[1]:>10,} cases")
        
        print("\n" + "="*70)
        print("✅ QUERY COMPLETE (all operations offline)")
        print("="*70)
        print(f"\n   Database ready for VERDICT integration")
        print(f"   {total:,} cases available for AI analysis\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

