#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to merge medical databases into clinic.db.
Copies clinical-grade case templates, conditions, and terminologies.
"""

import os
import sqlite3

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLINIC_DB = os.path.join(PROJECT_DIR, 'data', 'db', 'clinic.db')
MEDICAL_DB = os.path.join(PROJECT_DIR, 'data', 'db', 'medical.db')

def merge_databases():
    if not os.path.exists(MEDICAL_DB):
        print(f"Error: Source database not found at {MEDICAL_DB}")
        return
        
    print(f"Opening connection to {CLINIC_DB}...")
    conn = sqlite3.connect(CLINIC_DB)
    cursor = conn.cursor()
    
    # Attach medical.db
    cursor.execute(f"ATTACH DATABASE '{MEDICAL_DB}' AS medical")
    
    tables_to_copy = [
        "case_attachments",
        "case_templates",
        "chunks",
        "ingestion_log",
        "medical_conditions",
        "medical_guidelines",
        "medical_knowledge",
        "medical_terminology",
        "medical_treatments"
    ]
    
    for table in tables_to_copy:
        print(f"Merging table: {table}...")
        try:
            # Check if table already exists in main database
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            exists = cursor.fetchone()
            
            if exists:
                print(f"  -> Table '{table}' already exists in clinic.db. Skipping creation, appending new records...")
                # Fetch columns
                cursor.execute(f"PRAGMA table_info({table})")
                cols = [c[1] for c in cursor.fetchall()]
                col_names = ", ".join(cols)
                cursor.execute(f"INSERT OR IGNORE INTO {table} ({col_names}) SELECT {col_names} FROM medical.{table}")
            else:
                # Create table copy
                cursor.execute(f"CREATE TABLE {table} AS SELECT * FROM medical.{table}")
                print(f"  -> Table '{table}' successfully cloned and populated.")
                
        except Exception as e:
            print(f"Error merging table {table}: {e}")
            
    conn.commit()
    cursor.execute("DETACH DATABASE medical")
    conn.close()
    print("\nDatabase merge operation completed successfully!")

if __name__ == '__main__':
    merge_databases()
