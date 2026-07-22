#!/bin/bash
echo "🚀 Applying Llama Server Service Updates..."
cp /tmp/llama-server.service /etc/systemd/system/llama-server.service
systemctl daemon-reload
systemctl enable --now llama-server.service
systemctl restart llama-server.service
echo "✅ Service updated and restarted successfully!"
echo "You can check the status with: systemctl status llama-server.service"
