# VERDICT Bulk Data Pipeline

## Overview

This system **eliminates API timeouts** by downloading bulk case law datasets once and querying locally. After the initial download, **no network connection is required**.

### Why Bulk-First?

❌ **API Problems:**
- Rate limits (100-5000 requests/day)
- Timeouts and 403 errors
- Slow (one request per case)
- Requires authentication
- Unreliable for large datasets

✅ **Bulk Download Benefits:**
- Download millions of cases once
- Query locally at full speed
- No rate limits
- Works offline after setup
- Repeatable and reliable

## Quick Start

```bash
cd /Users/white_roze/LAwI/backend

# 1. Initialize
make init

# 2. Edit .env with dataset URL (examples provided)
nano .env

# 3. Download bulk data (one-time, ~5-60 min depending on dataset)
make bulk

# 4. Extract and ingest into SQLite (one-time, ~2-10 min)
make etl

# 5. Query locally (instant, works offline)
make query
make verify
```

## Available Datasets

### Harvard Caselaw Access Project (FREE)

**6.7 million cases** from US state and federal courts

**Small datasets** (for testing):
- Rhode Island: ~200MB, ~50K cases
  ```
  PRIMARY_URLS=https://api.case.law/v1/bulk/exports/rhode-island/rhode-island.zip
  ```

- Arkansas: ~500MB, ~200K cases
  ```
  PRIMARY_URLS=https://api.case.law/v1/bulk/exports/arkansas/arkansas.zip
  ```

**Medium datasets**:
- Illinois: ~2GB, ~500K cases
  ```
  PRIMARY_URLS=https://api.case.law/v1/bulk/exports/illinois/illinois.zip
  ```

- California: ~8GB, ~1.5M cases
  ```
  PRIMARY_URLS=https://api.case.law/v1/bulk/exports/california/california.zip
  ```

**Full dataset**: ~35GB compressed, all 6.7M cases
```
PRIMARY_URLS=https://api.case.law/v1/bulk/exports/
```

Browse all: https://case.law/bulk/download/

### CourtListener (FREE)

**Millions of federal court opinions**, updated monthly

**Federal Opinions** (recent):
```
PRIMARY_URLS=https://storage.courtlistener.com/bulk-data/opinions/opinions-2024-11.tar.gz
```

**Update monthly** (change date: `opinions-YYYY-MM.tar.gz`). The full listing of currently published archives lives at the REST index:
```
https://www.courtlistener.com/api/rest/v4/
```
and the bulk-data helper page that enumerates the filenames you can download is still at:
```
https://www.courtlistener.com/api/bulk-info/
```

> Tip: These URLs are static file downloads hosted from CourtListener's `storage.courtlistener.com` domain. Unlike the REST API endpoints, they'll start downloading immediately when you paste them in the browser. If you prefer navigating the JSON REST API, start from `https://www.courtlistener.com/api/rest/v4/` and follow the `bulk-data` links to locate the most recent archives.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  BULK DOWNLOAD (One-Time)                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ Primary URL │→ │ Mirror URLs  │→ │ Local Storage  │    │
│  │ (Harvard)   │  │ (HuggingFace)│  │ data/raw/*.zip │    │
│  └─────────────┘  └──────────────┘  └────────────────┘    │
│         ↓ Retry + Backoff + Resume                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  ETL PIPELINE (One-Time)                                    │
│  ┌──────────┐  ┌───────────┐  ┌─────────────────────┐     │
│  │ Extract  │→ │ Normalize │→ │ SQLite (Indexed)    │     │
│  │ ZIP/TAR  │  │ JSON      │  │ data/caselaw.db     │     │
│  └──────────┘  └───────────┘  └─────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  LOCAL QUERIES (Instant, Offline)                          │
│  ┌────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ SQL Query  │→ │ Indexed Lookup │→ │ Results         │  │
│  │ (no network)│  │ (ms response) │  │ (millions/sec)  │  │
│  └────────────┘  └────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
backend/
├── Makefile                    # Main commands
├── .env                        # Your configuration (from example)
├── config/
│   └── example.env            # Template configuration
├── data/                      # (gitignored)
│   ├── raw/                   # Downloaded archives
│   ├── processed/             # Extracted JSON files
│   ├── cache/                 # API cache (fallback only)
│   └── caselaw.db            # SQLite database (main store)
├── scripts/
│   └── fetch_bulk.sh         # Download script with retries
└── src/
    ├── bulk_ingest.py        # ETL pipeline
    ├── local_query.py        # Query examples
    └── util/
        ├── backoff.py        # Retry logic
        └── io.py             # I/O utilities
```

## Features

### ✅ Robust Download
- **Resume support**: Interrupted downloads continue from where they left off
- **Mirror fallback**: Tries Hugging Face, Internet Archive if primary fails
- **Exponential backoff**: Smart retry with jitter
- **SHA256 verification**: Optional checksum validation
- **Idempotent**: Re-running does nothing if data already downloaded

### ✅ Fast Local Queries
- **SQLite indexes**: Optimized for court, date, citation lookups
- **Offline operation**: Works without network after setup
- **Millions of cases**: Query entire state case law in milliseconds
- **Flexible schema**: Handles Harvard CAP, CourtListener, and custom formats

### ✅ Production Ready
- **PRAGMA WAL**: Write-Ahead Logging for concurrency
- **Batch commits**: Efficient ingestion
- **Error handling**: Continues on parse errors
- **Progress reporting**: Clear logs at each step

## Example Workflows

### Quick Test (Rhode Island - 200MB)

```bash
# Edit .env
echo 'PRIMARY_URLS=https://api.case.law/v1/bulk/exports/rhode-island/rhode-island.zip' >> .env

# Download + ETL + Query
make test
```

**Result**: ~50,000 real Rhode Island cases in local SQLite, queryable offline

### Production (California + New York)

```bash
# Edit .env
cat > .env << 'EOF'
PRIMARY_URLS=https://api.case.law/v1/bulk/exports/california/california.zip,https://api.case.law/v1/bulk/exports/new-york/new-york.zip
DB_PATH_SQLITE=data/caselaw.db
EOF

# Download (may take 30-60 min for large states)
make bulk

# Ingest (may take 10-20 min)
make etl

# Query (instant)
make query
```

**Result**: ~3 million real cases from CA + NY

### Federal Cases (CourtListener)

```bash
# Edit .env with current month's dump
echo 'PRIMARY_URLS=https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data/opinions/opinions-2024-11.tar.gz' >> .env

make bulk && make etl && make query
```

## Integration with VERDICT

Once you have the local database, integrate it into VERDICT:

```python
# In standalone_server.py

import sqlite3

DB_PATH = "data/caselaw.db"

def load_cases_from_local_db(limit=100):
    """Load real cases from local SQLite DB"""
    cases = []
    
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        
        for row in con.execute("""
            SELECT id, title, citation, court, decision_date, jurisdiction, case_type
            FROM cases
            WHERE title IS NOT NULL
            ORDER BY decision_date DESC
            LIMIT ?
        """, (limit,)):
            cases.append({
                "id": row['id'],
                "title": row['title'],
                "citation": row['citation'],
                "court": row['court'],
                "date": row['decision_date'],
                "jurisdiction": row['jurisdiction'],
                "case_type": row['case_type'] or 'general'
            })
    
    return cases

# Use in startup
real_cases = load_cases_from_local_db(limit=100)
```

## Troubleshooting

### "No such file or directory: data/raw"
```bash
make init
```

### "No JSON files found"
```bash
# Download first
make bulk
```

### "Download failed"
```bash
# Check URL in .env
# Try mirror URLs
# Check network connection
```

### "Database locked"
```bash
# Close any open connections
# SQLite uses WAL mode to prevent most locking
```

## Performance

| Operation | Time | Network |
|-----------|------|---------|
| Download Rhode Island | ~2-5 min | ✅ Required |
| Download Illinois | ~10-20 min | ✅ Required |
| Download California | ~30-60 min | ✅ Required |
| Extract archives | ~1-5 min | ❌ Offline |
| ETL to SQLite | ~2-10 min | ❌ Offline |
| Query 1M cases | <100ms | ❌ Offline |
| Subsequent queries | <10ms | ❌ Offline |

## Data Sources

### Harvard CAP
- **Coverage**: US state and federal courts
- **Cases**: 6.7 million
- **Format**: JSON in ZIP archives
- **License**: Open access
- **URL**: https://case.law/

### CourtListener  
- **Coverage**: US federal courts
- **Cases**: Millions (updated monthly)
- **Format**: JSON in TAR.GZ archives
- **License**: Public domain
- **URL**: https://www.courtlistener.com/

## Next Steps

1. **Start small**: Test with Rhode Island (~200MB, 5 min setup)
2. **Scale up**: Download your target jurisdiction
3. **Integrate**: Connect local DB to VERDICT backend
4. **Analyze**: Use OpenAI to analyze cases from local DB

Your system will then have:
- ✅ **Millions of REAL cases**
- ✅ **Instant access** (no API calls)
- ✅ **Offline operation**
- ✅ **No rate limits**
- ✅ **Full legal precedents**

## Support

Run `make help` to see all available commands.

For issues with specific datasets, check:
- Harvard CAP docs: https://case.law/docs/site/
- CourtListener bulk: https://www.courtlistener.com/api/bulk-info/
