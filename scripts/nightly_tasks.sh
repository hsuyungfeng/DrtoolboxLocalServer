#!/bin/bash
# DrToolbox Nightly Self-Learning Orchestrator
# Scheduled to run every night at 3 AM

PROJECT_DIR="/home/hsuyungfeng/DrtoolboxLocalServer"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
LOG_FILE="$PROJECT_DIR/logs/nightly_tasks.log"

mkdir -p "$PROJECT_DIR/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Starting Nightly Self-Learning Process ==="

# 1. HIS Data Sync (Just implemented)
log "Running HIS Data Sync..."
$PYTHON_BIN "$PROJECT_DIR/scripts/nightly_his_sync.py" >> "$LOG_FILE" 2>&1

# 2. Clinical Analysis Refresh
log "Refreshing Clinical Insights..."
$PYTHON_BIN -c "from src.services.clinical_analyzer import clinical_analyzer; clinical_analyzer.extract_and_analyze()" >> "$LOG_FILE" 2>&1

# 3. Nightly Fact-Check (Web Grounding)
log "Performing Fact-Check on low-confidence interactions..."
$PYTHON_BIN "$PROJECT_DIR/scripts/nightly_fact_check.py" >> "$LOG_FILE" 2>&1

# 4. Simulated QA Generation & Cross-Doc Reasoning
log "Generating simulated QA and performing global reasoning..."
$PYTHON_BIN "$PROJECT_DIR/scripts/nightly_qa_generator.py" >> "$LOG_FILE" 2>&1

# 5. External Channel Polling (Google Maps Reviews)
log "Polling for new Google Maps reviews..."
$PYTHON_BIN -c "from src.services.google_maps_service import google_maps_service; google_maps_service.fetch_and_process_reviews()" >> "$LOG_FILE" 2>&1

log "=== Nightly Self-Learning Complete ==="
