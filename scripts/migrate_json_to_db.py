#!/usr/bin/env python3
"""
Migrate PageIndex JSON Files to SQLite RAG Database.

Scans data/pageindex/special/ and data/pageindex/general/ for *.pi.json files,
parses them, and inserts them into the page_index_trees table in data/db/rag.db.
"""

import os
import sys
import json
import sqlite3
import glob
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag_engine import RAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_json_to_db")

def main():
    # Setup RAG Engine (this will run _init_db and create the tables if they don't exist)
    rag = RAGEngine()
    db_path = rag.db_path
    logger.info(f"Connected to SQLite RAG database at {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find all JSON files
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    special_pattern = os.path.join(project_root, "data/pageindex/special/**/*.pi.json")
    general_pattern = os.path.join(project_root, "data/pageindex/general/**/*.pi.json")

    special_files = glob.glob(special_pattern, recursive=True)
    general_files = glob.glob(general_pattern, recursive=True)

    logger.info(f"Found {len(special_files)} special pageindex files.")
    logger.info(f"Found {len(general_files)} general pageindex files.")

    def migrate_files(files, category):
        migrated_count = 0
        error_count = 0
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                doc_id = data.get("id")
                if not doc_id:
                    # Reconstruct doc_id from file naming convention if missing in json
                    filename = os.path.basename(filepath)
                    if filename.endswith(".pi.json"):
                        filename = filename[:-8]
                    doc_id = os.path.join(project_root, "data/documents", category, filename)

                tree = data.get("tree", {})
                pre_op = tree.get("pre_op", "無相關資料")
                procedure = tree.get("procedure", "無相關資料")
                post_op_short = tree.get("post_op_short", "無相關資料")
                maintenance = tree.get("maintenance", "無相關資料")
                
                pre_notes = tree.get("pre_op_physician_notes")
                proc_notes = tree.get("procedure_physician_notes")
                post_notes = tree.get("post_op_short_physician_notes")
                maint_notes = tree.get("maintenance_physician_notes")
                
                summary_parts = [pre_op, procedure, post_op_short, maintenance]
                if pre_notes: summary_parts.append(pre_notes)
                if proc_notes: summary_parts.append(proc_notes)
                if post_notes: summary_parts.append(post_notes)
                if maint_notes: summary_parts.append(maint_notes)
                summary_text = " ".join([p for p in summary_parts if p])
                
                version = data.get("version", "2.0")
                indexed_at = data.get("indexed_at", "")
                
                # Delete existing doc_id to prevent UNIQUE constraint error
                cursor.execute("DELETE FROM page_index_trees WHERE doc_id = ?", (doc_id,))
                
                cursor.execute("""
                    INSERT INTO page_index_trees 
                    (doc_id, category, pre_op, pre_op_physician_notes, procedure, procedure_physician_notes,
                     post_op_short, post_op_short_physician_notes, maintenance, maintenance_physician_notes,
                     summary_text, version, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (doc_id, category, pre_op, pre_notes, procedure, proc_notes,
                      post_op_short, post_notes, maintenance, maint_notes,
                      summary_text, version, indexed_at))
                      
                migrated_count += 1
            except Exception as e:
                logger.error(f"Error migrating {filepath}: {e}")
                error_count += 1
                
        conn.commit()
        logger.info(f"[{category}] Migrated: {migrated_count}, Errors: {error_count}")

    migrate_files(special_files, "special")
    migrate_files(general_files, "general")

    # Verify FTS tables integration and total counts
    cursor.execute("SELECT COUNT(*), category FROM page_index_trees GROUP BY category")
    logger.info("Verification results in database:")
    for count, cat in cursor.fetchall():
        logger.info(f"Category: {cat}, Count: {count}")

    conn.close()
    logger.info("Migration completed successfully.")

if __name__ == "__main__":
    main()
