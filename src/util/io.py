"""
I/O utilities for bulk data processing
"""
import os
import zipfile
import tarfile
import gzip
import json
import sqlite3
import pathlib
from datetime import datetime
from typing import Tuple

def ensure_dirs(*dirs):
    """Create directories if they don't exist"""
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        
def list_artifacts(raw_dir: str) -> list:
    """List all files in raw directory"""
    if not os.path.exists(raw_dir):
        return []
    return [str(pathlib.Path(raw_dir) / f) for f in os.listdir(raw_dir) if os.path.isfile(os.path.join(raw_dir, f))]

def extract_if_archive(path: str, out_dir: str) -> bool:
    """
    Extract archive if it's a ZIP, TAR, TAR.GZ, or GZ file
    
    Returns:
        True if extracted, False if not an archive
    """
    path_lower = path.lower()
    
    try:
        # ZIP files
        if path_lower.endswith(".zip"):
            print(f"📦 [extract] Unzipping {os.path.basename(path)}...")
            with zipfile.ZipFile(path, 'r') as z:
                z.extractall(out_dir)
            print(f"   ✅ Extracted to {out_dir}")
            return True
        
        # TAR.GZ files
        elif path_lower.endswith((".tar.gz", ".tgz")):
            print(f"📦 [extract] Extracting {os.path.basename(path)}...")
            with tarfile.open(path, 'r:gz') as tar:
                tar.extractall(out_dir)
            print(f"   ✅ Extracted to {out_dir}")
            return True
        
        # TAR files
        elif path_lower.endswith(".tar"):
            print(f"📦 [extract] Extracting {os.path.basename(path)}...")
            with tarfile.open(path, 'r:') as tar:
                tar.extractall(out_dir)
            print(f"   ✅ Extracted to {out_dir}")
            return True
        
        # GZIP files (single file)
        elif path_lower.endswith(".gz") and not path_lower.endswith(".tar.gz"):
            print(f"📦 [extract] Decompressing {os.path.basename(path)}...")
            out_file = os.path.join(out_dir, os.path.basename(path)[:-3])  # Remove .gz
            with gzip.open(path, 'rb') as gz_in:
                with open(out_file, 'wb') as f_out:
                    f_out.write(gz_in.read())
            print(f"   ✅ Decompressed to {out_file}")
            return True
        
        return False
        
    except Exception as e:
        print(f"   ❌ Extraction error: {e}")
        return False

def get_db(db_kind: str, sqlite_path: str, duckdb_path: str) -> Tuple:
    """
    Get database connection
    
    Returns:
        (connection, kind)
    """
    if db_kind == "duckdb":
        try:
            import duckdb
            con = duckdb.connect(duckdb_path)
            return con, "duckdb"
        except ImportError:
            print("⚠️  DuckDB not installed, falling back to SQLite")
    
    con = sqlite3.connect(sqlite_path)
    return con, "sqlite"

def init_schema_sqlite(con):
    """Initialize SQLite schema for case law data"""
    con.execute("""
    CREATE TABLE IF NOT EXISTS cases(
      id TEXT PRIMARY KEY,
      court TEXT,
      citation TEXT,
      decision_date TEXT,
      title TEXT,
      jurisdiction TEXT,
      reporter TEXT,
      case_type TEXT,
      raw_path TEXT,
      full_text_available INTEGER DEFAULT 0,
      inserted_at TEXT DEFAULT (datetime('now'))
    );""")
    
    # Indexes for performance
    con.execute("CREATE INDEX IF NOT EXISTS idx_cases_date ON cases(decision_date);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cases_court ON cases(court);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cases_citation ON cases(citation);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cases_jurisdiction ON cases(jurisdiction);")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cases_type ON cases(case_type);")
    
    con.commit()
    print("✅ SQLite schema initialized")

def get_db_stats(con, kind: str = "sqlite") -> dict:
    """Get database statistics"""
    if kind == "sqlite":
        cursor = con.cursor()
        
        # Total count
        total = cursor.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        
        # By court
        by_court = cursor.execute("""
            SELECT court, COUNT(*) as cnt 
            FROM cases 
            WHERE court IS NOT NULL
            GROUP BY court 
            ORDER BY cnt DESC 
            LIMIT 5
        """).fetchall()
        
        # Date range
        date_range = cursor.execute("""
            SELECT MIN(decision_date), MAX(decision_date) 
            FROM cases 
            WHERE decision_date IS NOT NULL
        """).fetchone()
        
        return {
            "total_cases": total,
            "top_courts": by_court,
            "date_range": date_range
        }
    
    return {"total_cases": 0}

