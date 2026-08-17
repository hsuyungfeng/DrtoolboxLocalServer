#!/bin/bash
fuser -k 5000/tcp || true
sleep 1
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH=.
nohup uv run python src/api/app.py > last_server_run.log 2>&1 &
echo "Server started on port 5000."
