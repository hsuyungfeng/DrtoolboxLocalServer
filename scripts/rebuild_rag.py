#!/usr/bin/env python3
"""
Rebuild RAG Collections script.

This script completely rebuilds the dual knowledge base (general_medical and clinic_specific)
from their respective source document directories.

Usage:
    uv run python scripts/rebuild_rag.py [--force]
"""

import os
import sys
import glob
import logging
import argparse

# Add src directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from rag.ingest import DocumentIngestor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rebuild_rag")

def rebuild_collection(collection_name: str, docs_dir: str, force_clear: bool = False):
    """Rebuild a specific collection from a directory of documents."""
    logger.info(f"--- Rebuilding Collection: {collection_name} ---")
    
    # Ensure source directory exists
    os.makedirs(docs_dir, exist_ok=True)
    
    # Get ingestor
    ingestor = DocumentIngestor(
        chroma_dir="data/rag/chroma/",
        collection_name=collection_name
    )
    
    # Force clear if requested
    if force_clear:
        logger.info(f"Clearing existing collection: {collection_name}")
        ingestor.delete_collection(confirm=True)
        # Re-initialize after deletion
        ingestor._init_chroma()
        
    # Find all supported documents
    files = []
    for ext in ingestor.supported_formats:
        files.extend(glob.glob(os.path.join(docs_dir, f"**/*{ext}"), recursive=True))
        
    if not files:
        logger.warning(f"No supported documents found in {docs_dir}. Please add files and run again.")
        return
        
    logger.info(f"Found {len(files)} documents to ingest.")
    
    # Batch ingest
    results = ingestor.ingest_batch(files)
    
    # Print summary
    success = sum(1 for r in results if r.embedded)
    failed = len(results) - success
    logger.info(f"Rebuild Complete for {collection_name}: {success} successful, {failed} failed.")
    for result in results:
        if not result.embedded:
            logger.error(f"Failed: {result.source} - Errors: {result.errors}")


def main():
    parser = argparse.ArgumentParser(description="Rebuild RAG databases")
    parser.add_argument("--force", action="store_true", help="Force clear existing collections before rebuilding")
    args = parser.parse_args()
    
    logger.info("Starting Federated RAG Database Rebuild")
    
    if args.force:
        logger.warning("FORCE FLAG DETECTED. Existing RAG data will be wiped and rebuilt from source files.")
        
    # 1. Rebuild Medical Domain
    rebuild_collection(
        collection_name="general_medical",
        docs_dir="data/rag/general_docs/",
        force_clear=args.force
    )
    
    # 2. Rebuild Clinical Domain
    rebuild_collection(
        collection_name="clinic_specific",
        docs_dir="data/rag/clinic_docs/",
        force_clear=args.force
    )
    
    logger.info("--- RAG Database Rebuild Finished ---")
    logger.info("The system is now ready to serve intent-routed queries.")

if __name__ == "__main__":
    main()
