#!/usr/bin/env bash
# immo-search — execution script
# Usage:
#   bash run.sh          → daily run (fetch new listings, send alert)
#   bash run.sh --week   → weekly digest (best of the past 7 days, sent Saturday)
# Scheduled via macOS launchd:
#   com.immo-search.plist        → daily 07:30
#   com.immo-search-weekly.plist → Saturday 09:00

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [[ -f ".env" ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Ensure log directory exists
mkdir -p logs output

# Determine log file based on mode
MODE_FLAG="${1:-}"
if [[ "$MODE_FLAG" == "--week" ]]; then
    LOG_FILE="logs/weekly.log"
    LABEL="immo-search (weekly digest)"
else
    LOG_FILE="logs/run.log"
    LABEL="immo-search"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting ${LABEL}..." | tee -a "$LOG_FILE"

uv run python -m app.main $MODE_FLAG 2>&1 | tee -a "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${LABEL} completed." | tee -a "$LOG_FILE"
