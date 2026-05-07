#!/bin/bash
# Ingest all documents from both knowledge base folders
# Usage: bash scripts/ingest_all.sh

cd "$(dirname "$0")/.."

echo "=== DrtoolboxLocalServer Document Ingestion ==="
echo ""
echo "Ingesting documents from both knowledge bases..."
echo ""

# Create Python script inline to handle ingestion
python3 << 'EOF'
import os
import sys
import json
from pathlib import Path
from src.rag.ingest import DocumentIngestor

# Load config
config = {}
try:
    with open('config/ingest_config.json', 'r') as f:
        config = json.load(f)
except Exception as e:
    print(f"Warning: Could not load config: {e}")
    config = {
        "chroma": {
            "path": "data/rag/chroma_new/",
            "collections": {
                "general_medical": "general_medical",
                "clinic_specific": "clinic_specific",
            },
        },
        "document_folders": {
            "general_medical": "data/rag/general_docs/",
            "clinic_specific": "data/rag/clinic_docs/",
        },
    }

chroma_path = config.get("chroma", {}).get("path", "data/rag/chroma_new/")
doc_folders = config.get("document_folders", {})
collections = config.get("chroma", {}).get("collections", {})

supported_formats = {'.txt', '.pdf', '.docx'}
total_ingested = 0
total_errors = 0

for collection_key, folder_path in doc_folders.items():
    collection_name = collections.get(collection_key, collection_key)

    print(f"\n[{collection_key}] Scanning: {folder_path}")

    if not os.path.exists(folder_path):
        print(f"  ⚠️  Folder does not exist, skipping")
        continue

    # Initialize ingestor for this collection
    ingestor = DocumentIngestor(
        chroma_dir=chroma_path,
        collection_name=collection_name,
        chunk_size=512,
        chunk_overlap=50,
    )
    ingestor._init_chroma()

    # Walk through folder recursively
    ingested_files = []
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            # Skip hidden files and gitkeep
            if filename.startswith('.'):
                continue

            file_path = os.path.join(root, filename)
            ext = Path(filename).suffix.lower()

            # Only process supported formats
            if ext not in supported_formats:
                continue

            try:
                print(f"  → Ingesting: {filename}...", end=" ", flush=True)
                result = ingestor.ingest(file_path, metadata={"collection": collection_key})

                if result.embedded:
                    print(f"✓ ({result.chunks} chunks)")
                    ingested_files.append({
                        "file": filename,
                        "chunks": result.chunks,
                        "duration_ms": result.duration_ms,
                    })
                    total_ingested += result.chunks
                else:
                    print(f"⚠️  (No chunks created)")

            except Exception as e:
                print(f"✗ Error: {e}")
                total_errors += 1

    # Summary for this collection
    print(f"\n  Summary: {len(ingested_files)} files, {sum(f['chunks'] for f in ingested_files)} total chunks")
    if ingested_files:
        for f in ingested_files:
            print(f"    - {f['file']}: {f['chunks']} chunks ({f['duration_ms']:.0f}ms)")

print(f"\n{'='*50}")
print(f"✓ Total chunks ingested: {total_ingested}")
if total_errors > 0:
    print(f"⚠️  Errors encountered: {total_errors}")
print(f"{'='*50}")
print(f"\nVerify collections with: GET /api/v1/rag/collection")
print(f"Query example: curl -X POST http://localhost:5000/api/v1/rag/query \\")
print(f'  -H "Content-Type: application/json" \\')
print(f'  -d \'{{"prompt":"test","collection":"both"}}\'')

EOF
