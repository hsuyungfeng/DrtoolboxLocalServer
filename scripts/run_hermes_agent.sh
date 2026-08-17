#!/bin/bash
# Hermes Agent Runner
# Starts the Hermes Agent API server on port 8642.

HERMES_PORT=8642
fuser -k ${HERMES_PORT}/tcp || true
sleep 1
export PYTHONPATH=.
echo "🚀 Starting Hermes Agent Server on port $HERMES_PORT..."
nohup uv run python src/agent/hermes_server.py > logs/hermes_agent.log 2>&1 &

echo "✅ Hermes Agent Server started in background."
