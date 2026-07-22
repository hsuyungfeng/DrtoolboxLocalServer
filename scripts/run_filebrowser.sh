#!/bin/bash
# FileBrowser Runner - Task 11.4
# Downloads and runs the standalone FileBrowser binary on port 8081.

FB_PORT=8081
FB_DB="data/db/filebrowser.db"
FB_ROOT="data/documents"

# Ensure directories exist
mkdir -p data/db
mkdir -p data/documents

FB_BIN="$HOME/.local/bin/filebrowser"

# Check if filebrowser is installed
if [ ! -f "$FB_BIN" ]; then
    echo "📥 FileBrowser not found. Downloading locally..."
    mkdir -p ~/.local/bin
    curl -fsSL https://github.com/filebrowser/filebrowser/releases/download/v2.30.0/linux-amd64-filebrowser.tar.gz | tar -xz -C ~/.local/bin filebrowser
    chmod +x "$FB_BIN"
fi

echo "🚀 Starting FileBrowser on port $FB_PORT..."
echo "📂 Managing: $FB_ROOT"

# Run FileBrowser in background
# -a: address, -p: port, -r: root, -d: database
$FB_BIN -a 0.0.0.0 -p $FB_PORT -r $FB_ROOT -d $FB_DB --noauth > logs/filebrowser.log 2>&1 &

echo "✅ FileBrowser started in background."
