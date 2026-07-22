#!/bin/bash
echo "🛑 關閉佔用 8080 port 的所有進程..."
fuser -k 8080/tcp
sleep 2

echo "🚀 重啟 Llama Server..."
systemctl restart llama-server.service
systemctl status llama-server.service --no-pager
echo "✅ 已經重啟並重新綁定 8080 port！"
