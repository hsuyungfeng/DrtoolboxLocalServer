#!/bin/bash
# Hermes Agent Runner - Task 11.5
# Starts the Hermes Agent API server on port 8642.

HERMES_PORT=8642

echo "🚀 Starting Hermes Agent Server on port $HERMES_PORT..."
nohup ./.venv/bin/python src/agent/hermes_server.py > logs/hermes_agent.log 2>&1 &

echo "✅ Hermes Agent Server started in background."
