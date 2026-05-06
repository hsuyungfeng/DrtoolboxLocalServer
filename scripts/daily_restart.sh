#!/bin/bash
#
# Daily restart script for DrToolbox Local Server
# Runs at 2 AM daily to ensure 24h stability (D-12)
#
# This script:
# 1. Gracefully stops the Flask API server
# 2. Clears any caches (if applicable)
# 3. Restarts the server
# 4. Logs the restart to logs/restart.log
#

set -e

# Configuration
PROJECT_DIR="/home/hsu/DrtoolboxLocalServer"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/restart.log"
PID_FILE="${PROJECT_DIR}/server.pid"
FLASK_PORT="5000"

# Create log directory if not exists
mkdir -p "${LOG_DIR}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=== Daily restart initiated ==="

# Step 1: Find and stop Flask server gracefully
log "Stopping Flask server..."

# Try multiple methods to find and stop the server
if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        log "Sending SIGTERM to process ${PID}"
        kill -TERM "${PID}" 2>/dev/null || true
        
        # Wait up to 30 seconds for graceful shutdown
        for i in {1..30}; do
            if ! kill -0 "${PID}" 2>/dev/null; then
                log "Process ${PID} stopped gracefully"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "${PID}" 2>/dev/null; then
            log "Force killing process ${PID}"
            kill -9 "${PID}" 2>/dev/null || true
        fi
    fi
    rm -f "${PID_FILE}"
fi

# Also try to kill by port
if command -v lsof &> /dev/null; then
    LSOF_PID=$(lsof -ti:${FLASK_PORT} 2>/dev/null || true)
    if [ -n "${LSOF_PID}" ]; then
        log "Killing process on port ${FLASK_PORT}: ${LSOF_PID}"
        kill -TERM "${LSOF_PID}" 2>/dev/null || true
    fi
fi

# Also try pkill
if command -v pkill &> /dev/null; then
    pkill -f "flask run" 2>/dev/null || true
    pkill -f "src.api.app" 2>/dev/null || true
fi

log "Server stopped"

# Step 2: Clear caches if they exist
log "Checking for caches to clear..."

# Clear Python cache
find "${PROJECT_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Clear any temporary inference caches
if [ -d "${PROJECT_DIR}/.cache" ]; then
    rm -rf "${PROJECT_DIR}/.cache" 2>/dev/null || true
    log "Cleared .cache directory"
fi

log "Cache clearing complete"

# Step 3: Restart the server
log "Starting Flask server..."

cd "${PROJECT_DIR}"

# Start server in background, save PID
nohup python -m src.api.app > "${LOG_DIR}/server.log" 2>&1 &
NEW_PID=$!
echo "${NEW_PID}" > "${PID_FILE}"

log "Server started with PID ${NEW_PID}"

# Wait for server to be ready (max 30 seconds)
log "Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s "http://localhost:${FLASK_PORT}/health" > /dev/null 2>&1; then
        log "Server is ready after ${i} seconds"
        break
    fi
    if [ $i -eq 30 ]; then
        log "WARNING: Server may not have started properly"
    fi
    sleep 1
done

log "=== Daily restart complete ==="
log ""

exit 0