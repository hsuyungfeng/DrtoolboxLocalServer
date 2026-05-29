#!/bin/bash
fuser -k 5000/tcp
pkill -9 python
sleep 2
nohup /home/hsuyungfeng/DrtoolboxLocalServer/.venv/bin/python src/api/app.py > last_server_run.log 2>&1 &
echo "Server started."
