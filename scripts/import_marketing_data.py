#!/usr/bin/env python3
"""
Marketing Data Import Script (Multimodal RAG)

This script recursively scans a directory containing marketing graphics, 
presentations, and documents, performs OCR on images, and ingests them 
into the `clinic_specific` RAG collection.

Usage:
    python scripts/import_marketing_data.py --dir "/media/hsu/软件/行銷圖文檔案整理"
    python scripts/import_marketing_data.py --test-run
"""

import os
import sys
import argparse
import tempfile
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Add src to path so we can import rag module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from rag.ingest import DocumentIngestor

# OCR Dependencies
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("Pillow or pytesseract not installed. Image OCR will be disabled.")

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}

def clean_ocr_text(text: str) -> str:
    """Clean up noise from OCR text."""
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip very short lines that are likely noise unless they have numbers/currency
        if not line or (len(line) < 2 and not any(c.isdigit() for c in line)):
            continue
        cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)

def process_image(file_path: str, ingestor: DocumentIngestor) -> bool:
    """Process an image file using OCR and ingest it."""
    if not OCR_AVAILABLE:
        logger.error(f"Cannot process image {file_path} because OCR dependencies are missing.")
        return False
        
    try:
        logger.info(f"Running OCR on: {file_path}")
        img = Image.open(file_path)
        
        # Use Traditional Chinese + English for OCR
        text = pytesseract.image_to_string(img, lang='chi_tra+eng')
        cleaned_text = clean_ocr_text(text)
        
        if not cleaned_text.strip():
            logger.warning(f"No meaningful text extracted from {file_path}")
            return False
            
        # Create a temporary text file to reuse the chunking logic of DocumentIngestor
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
            # Prepend the filename as context
            context_header = f"檔案名稱 (File Name): {os.path.basename(file_path)}\n\n"
            temp_file.write(context_header + cleaned_text)
            temp_path = temp_file.name
            
        try:
            # Define rich metadata
            metadata = {
                "source": os.path.basename(file_path),
                "full_path": file_path,
                "category": "marketing",
                "type": "image_ocr"
            }
            
            # Extract parent folder as sub-category (e.g., '價目表')
            parent_dir = Path(file_path).parent.name
            if parent_dir:
                metadata["sub_category"] = parent_dir
                
            result = ingestor.ingest(temp_path, metadata=metadata)
            logger.info(f"✅ Ingested {result.chunks} chunks from image {os.path.basename(file_path)}")
            return True
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"❌ Failed to process image {file_path}: {e}")
        return False

def process_document(file_path: str, ingestor: DocumentIngestor) -> bool:
    """Process a supported document file."""
    try:
        logger.info(f"Processing document: {file_path}")
        
        metadata = {
            "source": os.path.basename(file_path),
            "full_path": file_path,
            "category": "marketing",
            "type": "document"
        }
        
        parent_dir = Path(file_path).parent.name
        if parent_dir:
            metadata["sub_category"] = parent_dir
            
        result = ingestor.ingest(file_path, metadata=metadata)
        logger.info(f"✅ Ingested {result.chunks} chunks from {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process document {file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Ingest marketing data into clinic_specific collection")
    parser.add_argument("--dir", type=str, default="/media/hsu/软件/行銷圖文檔案整理", help="Directory to scan")
    parser.add_argument("--test-run", action="store_true", help="Run on a small subset of files only (max 3)")
    args = parser.parse_args()
    
    target_dir = args.dir
    if not os.path.exists(target_dir):
        logger.error(f"Directory not found: {target_dir}")
        sys.exit(1)
        
    # Initialize ingestor for the clinic specific collection
    # Note: Using the standard Chroma config loaded in rag.py
    logger.info("Initializing DocumentIngestor for 'clinic_specific' collection...")
    
    # We create the ingestor explicitly pointing to the standard path
    # but specifically targeting the clinic collection
    ingestor = DocumentIngestor(
        chroma_dir="data/rag/chroma_new/",
        collection_name="clinic_specific"
    )
    
    # Pre-init check
    ingestor._init_chroma()
    
    supported_doc_formats = ingestor.supported_formats
    
    stats = {"images": 0, "documents": 0, "failed": 0, "skipped": 0}
    processed_count = 0
    max_test_files = 3
    
    logger.info(f"Scanning directory: {target_dir}")
    
    for root, _, files in os.walk(target_dir):
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            ext = Path(file).suffix.lower()
            
            if ext in IMAGE_EXTENSIONS:
                success = process_image(file_path, ingestor)
                if success:
                    stats["images"] += 1
                else:
                    stats["failed"] += 1
                processed_count += 1
                
            elif ext in supported_doc_formats:
                success = process_document(file_path, ingestor)
                if success:
                    stats["documents"] += 1
                else:
                    stats["failed"] += 1
                processed_count += 1
                
            else:
                stats["skipped"] += 1
                
            if args.test_run and processed_count >= max_test_files:
                logger.info(f"Test run limit reached ({max_test_files} files). Stopping.")
                break
                
        if args.test_run and processed_count >= max_test_files:
            break
            
    logger.info("--- Import Complete ---")
    logger.info(f"Images successfully processed: {stats['images']}")
    logger.info(f"Documents successfully processed: {stats['documents']}")
    logger.info(f"Failed files: {stats['failed']}")
    logger.info(f"Skipped files (unsupported): {stats['skipped']}")

if __name__ == "__main__":
    main()
