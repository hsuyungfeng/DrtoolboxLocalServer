#!/usr/bin/env python3
"""
Ingest documents from both general_docs and clinic_docs into separate Chroma collections.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.ingest import DocumentIngestor


def ingest_collection(collection_key: str, folder_path: str, collection_name: str):
    """Ingest all documents from a folder into a Chroma collection."""
    print(f"\n{'='*60}")
    print(f"📚 Ingesting {collection_key.upper()} Collection")
    print(f"   Collection: {collection_name}")
    print(f"   Folder: {folder_path}")
    print(f"{'='*60}")

    if not os.path.isdir(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return 0, 0

    # Initialize ingestor for this collection
    ingestor = DocumentIngestor(
        chroma_dir="data/rag/chroma_new/",
        collection_name=collection_name,
        chunk_size=512,
        chunk_overlap=50,
    )
    ingestor._init_chroma()

    # Verify collection was created
    print(f"   Initial collection count: {ingestor.collection.count()}")

    supported_formats = {'.txt', '.pdf', '.docx', '.json'}
    total_ingested = 0
    total_errors = 0

    # Walk through folder recursively
    ingested_files = []
    for root, dirs, files in os.walk(folder_path):
        for filename in sorted(files):
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
                    print(f"✓ ({result.chunks} chunks, {result.duration_ms:.0f}ms)")
                    ingested_files.append({
                        "file": filename,
                        "chunks": result.chunks,
                        "duration_ms": result.duration_ms,
                    })
                    total_ingested += result.chunks
                else:
                    print(f"⚠️   (No chunks created)")

            except Exception as e:
                print(f"✗ Error: {e}")
                total_errors += 1

    # Summary for this collection
    if ingested_files:
        print(f"\n  Summary: {len(ingested_files)} files, {sum(f['chunks'] for f in ingested_files)} total chunks")
        for f in ingested_files:
            print(f"    - {f['file']}: {f['chunks']} chunks ({f['duration_ms']:.0f}ms)")

    # Get collection info
    info = ingestor.get_collection_info()
    print(f"\n  Collection Info:")
    print(f"    - Total documents in collection: {info['count']}")

    # Verify by querying the collection directly
    try:
        collection_data = ingestor.collection.get()
        actual_count = len(collection_data['ids']) if collection_data['ids'] else 0
        print(f"    - Verified document count (via .get()): {actual_count}")
    except Exception as e:
        print(f"    - Error verifying collection: {e}")

    return total_ingested, total_errors


def main():
    """Ingest both collections."""
    print("\n🚀 RAG Document Ingestion Pipeline")
    print("=" * 60)

    base_path = os.path.dirname(__file__)

    # Ingest general_docs (medical knowledge base)
    general_ingested, general_errors = ingest_collection(
        collection_key="general_medical",
        folder_path=os.path.join(base_path, "data/rag/general_docs"),
        collection_name="general_medical_docs"
    )

    # Ingest clinic_docs (clinic-specific protocols)
    clinic_ingested, clinic_errors = ingest_collection(
        collection_key="clinic_specific",
        folder_path=os.path.join(base_path, "data/rag/clinic_docs"),
        collection_name="clinic_specific_docs"
    )

    # Final summary
    print(f"\n{'='*60}")
    print("✅ INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"\n📊 Results:")
    print(f"   General Medical Collection:")
    print(f"     - Chunks ingested: {general_ingested}")
    print(f"     - Errors: {general_errors}")
    print(f"\n   Clinic Specific Collection:")
    print(f"     - Chunks ingested: {clinic_ingested}")
    print(f"     - Errors: {clinic_errors}")
    print(f"\n   Total:")
    print(f"     - Total chunks: {general_ingested + clinic_ingested}")
    print(f"     - Total errors: {general_errors + clinic_errors}")
    print(f"\n💾 Chroma database: data/rag/chroma_new/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
