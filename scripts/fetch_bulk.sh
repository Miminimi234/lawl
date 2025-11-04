#!/usr/bin/env bash
set -euo pipefail

URLS_RAW="${1:-${PRIMARY_URLS:-}}"
if [[ -z "$URLS_RAW" ]]; then
  echo "❌ Usage: fetch_bulk.sh \"URL1,URL2,...\"" >&2
  echo "   Or set PRIMARY_URLS in .env" >&2
  exit 1
fi

RAW_DIR="${RAW_DIR:-data/raw}"
mkdir -p "$RAW_DIR"

IFS=',' read -ra URLS <<< "$URLS_RAW"

download() {
  local url="$1"
  local fname="$(basename "${url%%\?*}")"
  local out="$RAW_DIR/$fname"

  # Check if already downloaded
  if [[ -f "$out" ]] && [[ -s "$out" ]]; then
    echo "✅ [cached] $fname already downloaded ($(du -h "$out" | awk '{print $1}'))"
    return 0
  fi

  echo "📡 [fetch] $url"
  echo "   ├─ Output: $out"
  
  local connect_timeout="${CONNECT_TIMEOUT:-10}"
  local max_retries="${MAX_RETRIES:-6}"
  local backoff_base="${BACKOFF_BASE:-2.0}"
  local backoff_cap="${BACKOFF_CAP:-60}"
  local jitter="${JITTER_SECS:-0.6}"
  
  for attempt in $(seq 1 $max_retries); do
    echo "   ├─ Attempt $attempt/$max_retries..."
    
    start_time=$(date +%s)
    
    # Try curl first (resume with -C -)
    if command -v curl >/dev/null 2>&1; then
      if curl -fL \
          --connect-timeout "$connect_timeout" \
          --max-time 0 \
          --retry 0 \
          -C - \
          --progress-bar \
          -o "$out" \
          "$url" 2>&1 | tr '\r' '\n' | grep -E '###|100' | tail -1; then
        
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        size=$(du -h "$out" | awk '{print $1}')
        
        echo "   └─ ✅ Downloaded $size in ${elapsed}s"
        return 0
      fi
    # Fallback to wget
    elif command -v wget >/dev/null 2>&1; then
      if wget -c \
          --timeout="$connect_timeout" \
          --tries=1 \
          --progress=bar:force \
          -O "$out" \
          "$url" 2>&1 | grep -E '%|saved'; then
        
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        size=$(du -h "$out" | awk '{print $1}')
        
        echo "   └─ ✅ Downloaded $size in ${elapsed}s"
        return 0
      fi
    else
      echo "   └─ ❌ Neither curl nor wget available"
      return 1
    fi

    # Calculate backoff with jitter
    if [[ $attempt -lt $max_retries ]]; then
      base_delay=$(python3 - <<PYTHON
import math
delay = min($backoff_cap, $backoff_base ** ($attempt - 1))
print(int(delay))
PYTHON
)
      
      jitter_val=$(python3 - <<PYTHON
import random
print(f"{random.uniform(0, $jitter):.2f}")
PYTHON
)
      
      total_delay=$(python3 - <<PYTHON
print(f"{$base_delay + $jitter_val:.1f}")
PYTHON
)
      
      echo "   ├─ ⏸️  Retry in ${total_delay}s (backoff + jitter)..."
      sleep "$total_delay"
    fi
  done
  
  echo "   └─ ❌ Failed after $max_retries attempts"
  return 1
}

verify_checksum() {
  local file="$1"
  local sha_url="${2}.sha256"
  local fname="$(basename "$file")"
  
  # Try downloading checksum file
  if curl -fsSL "$sha_url" -o "$file.sha256" 2>/dev/null; then
    echo "🔐 [verify] Checking SHA256..."
    if (cd "$RAW_DIR" && shasum -a 256 -c "$fname.sha256" 2>&1 | grep -q OK); then
      echo "   └─ ✅ Checksum verified"
      return 0
    else
      echo "   └─ ❌ Checksum mismatch!"
      return 1
    fi
  # Check environment variable
  elif [[ -n "${SHA256_MAIN:-}" ]]; then
    echo "🔐 [verify] Checking SHA256 from .env..."
    echo "${SHA256_MAIN}  ${fname}" | (cd "$RAW_DIR" && shasum -a 256 -c - 2>&1 | grep -q OK)
    if [[ $? -eq 0 ]]; then
      echo "   └─ ✅ Checksum verified (.env)"
      return 0
    else
      echo "   └─ ❌ Checksum mismatch!"
      return 1
    fi
  else
    echo "ℹ️  [verify] No checksum provided; skipping verification"
    return 0
  fi
}

# Main download logic with mirror fallback
echo "============================================================"
echo "🏛️  VERDICT BULK DATA DOWNLOAD"
echo "============================================================"
echo ""

# Try primary URLs first
for url in "${URLS[@]}"; do
  echo "Trying PRIMARY: $url"
  
  if download "$url"; then
    fname="$(basename "${url%%\?*}")"
    out="$RAW_DIR/$fname"
    
    # Verify checksum
    if verify_checksum "$out" "$url"; then
      echo ""
      echo "✅ SUCCESS: $fname"
      echo "   Path: $out"
      echo "   Size: $(du -h "$out" | awk '{print $1}')"
      echo ""
      echo "Next step: make etl"
      exit 0
    else
      echo "⚠️  Checksum failed, trying mirrors..."
    fi
  else
    echo "⚠️  Download failed: $url"
  fi
  echo ""
done

# Try mirror URLs if primary failed
if [[ -n "${MIRROR_URLS:-}" ]]; then
  echo "🔄 Trying mirror URLs..."
  echo ""
  
  IFS=',' read -ra MIRRORS <<< "$MIRROR_URLS"
  
  for url in "${MIRRORS[@]}"; do
    [[ -z "$url" ]] && continue  # Skip empty URLs
    
    echo "Trying MIRROR: $url"
    
    if download "$url"; then
      fname="$(basename "${url%%\?*}")"
      out="$RAW_DIR/$fname"
      
      echo ""
      echo "✅ SUCCESS (from mirror): $fname"
      echo "   Path: $out"
      echo "   Size: $(du -h "$out" | awk '{print $1}')"
      echo ""
      echo "Next step: make etl"
      exit 0
    else
      echo "⚠️  Mirror failed: $url"
    fi
    echo ""
  done
fi

echo "❌ ERROR: All download attempts failed"
echo "   Primary URLs: ${#URLS[@]}"
if [[ -n "${MIRROR_URLS:-}" ]]; then
  IFS=',' read -ra MIRRORS <<< "$MIRROR_URLS"
  echo "   Mirror URLs: ${#MIRRORS[@]}"
else
  echo "   Mirror URLs: 0"
fi
exit 2

