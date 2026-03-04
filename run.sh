#!/usr/bin/env bash
# immo-search — daily execution script
# Usage: bash run.sh
# Scheduled via macOS launchd at 07:30 daily

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [[ -f ".env" ]]; then
    export $(grep -v '^#' .env | xargs)
fi

# Ensure log directory exists
mkdir -p logs output

# Run the agent
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting immo-search..." | tee -a logs/run.log

uv run python -m app.main 2>&1 | tee -a logs/run.log

echo "[$(date '+%Y-%m-%d %H:%M:%S')] immo-search completed." | tee -a logs/run.log
