#!/bin/bash
# Start all ecosystem services for DrtoolboxLocalServer

# 1. Start FileBrowser
bash scripts/run_filebrowser.sh

# 2. Start Hermes Agent API
bash scripts/run_hermes_agent.sh

# 3. Start Main Server
bash scripts/start_server.sh

echo "🌟 All services have been triggered."
echo "-------------------------------------"
echo "Main Dashboard: http://localhost:5000"
echo "FileBrowser:    http://localhost:8081"
echo "Hermes API:     http://localhost:8642"
echo "-------------------------------------"
