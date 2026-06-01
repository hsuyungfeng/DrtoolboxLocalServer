#!/bin/bash
# FileBrowser Runner - Task 11.4
# Downloads and runs the standalone FileBrowser binary on port 8081.

FB_PORT=8081
FB_DB="data/db/filebrowser.db"
FB_ROOT="data/documents"

# Ensure directories exist
mkdir -p data/db
mkdir -p data/documents

# Check if filebrowser is installed
if ! command -v filebrowser &> /dev/null
then
    echo "📥 FileBrowser not found. Downloading..."
    curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
fi

echo "🚀 Starting FileBrowser on port $FB_PORT..."
echo "📂 Managing: $FB_ROOT"

# Run FileBrowser in background
# -a: address, -p: port, -r: root, -d: database
filebrowser -a 0.0.0.0 -p $FB_PORT -r $FB_ROOT -d $FB_DB --noauth > logs/filebrowser.log 2>&1 &

echo "✅ FileBrowser started in background."
