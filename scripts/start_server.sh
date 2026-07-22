#!/bin/bash
fuser -k 5000/tcp
sleep 2
nohup ./.venv/bin/python src/api/app.py > last_server_run.log 2>&1 &
echo "Server started."
