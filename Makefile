SHELL := /bin/bash
ENV_FILE ?= .env
include $(ENV_FILE)
export $(shell sed 's/=.*//' $(ENV_FILE) 2>/dev/null)

.PHONY: help init bulk etl query verify clean test

help:
	@echo "VERDICT Bulk Data Pipeline"
	@echo ""
	@echo "Targets:"
	@echo "  init   - Create directories and .env"
	@echo "  bulk   - Download bulk case datasets"
	@echo "  etl    - Extract and ingest into local DB"
	@echo "  query  - Run sample local query"
	@echo "  verify - Check DB contents"
	@echo "  test   - Full pipeline test"
	@echo "  clean  - Remove all data"

init:
	@mkdir -p data/raw data/processed data/cache
	@cp -n config/example.env .env 2>/dev/null || true
	@echo "✅ Directories created"
	@echo "✅ Edit .env with PRIMARY_URLS and MIRROR_URLS"
	@echo ""
	@echo "Example bulk datasets:"
	@echo "  Harvard CAP: https://case.law/bulk/download/"
	@echo "  CourtListener: https://www.courtlistener.com/api/bulk-info/"

bulk: init
	@echo "📡 Downloading bulk datasets..."
	./scripts/fetch_bulk.sh

etl: init
	@echo "⚙️  Running ETL pipeline..."
	python3 src/bulk_ingest.py

query:
	@echo "🔍 Running sample query..."
	python3 src/local_query.py

verify:
	@echo "📊 Database statistics:"
	@echo ""
	@echo "Row count by court:"
	@sqlite3 $(DB_PATH_SQLITE) "SELECT court, COUNT(*) FROM cases GROUP BY court ORDER BY 2 DESC LIMIT 10;" 2>/dev/null || echo "No data yet"
	@echo ""
	@echo "Total cases:"
	@sqlite3 $(DB_PATH_SQLITE) "SELECT COUNT(*) FROM cases;" 2>/dev/null || echo "0"
	@echo ""
	@echo "Date range:"
	@sqlite3 $(DB_PATH_SQLITE) "SELECT MIN(decision_date), MAX(decision_date) FROM cases WHERE decision_date IS NOT NULL;" 2>/dev/null || echo "N/A"

test: init bulk etl verify
	@echo ""
	@echo "✅ Full pipeline test complete!"

clean:
	@echo "🗑️  Cleaning all data..."
	rm -rf data/*
	@echo "✅ Clean complete"

