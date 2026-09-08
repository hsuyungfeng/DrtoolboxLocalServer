#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to copy medical graph and clinical database tables from DrtoolboxLocalServer
into SoapVoice's local database directory, making SoapVoice database-independent.
"""

import os
import sqlite3
import shutil

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLINIC_DB = os.path.join(PROJECT_DIR, 'data', 'db', 'clinic.db')
SOAPVOICE_DB_DIR = '/home/hsuyungfeng/SoapVoice/data/local_db'
SOAPVOICE_DB = os.path.join(SOAPVOICE_DB_DIR, 'medical.db')

def copy_database():
    if not os.path.exists(CLINIC_DB):
        print(f"Error: Source clinic.db not found at {CLINIC_DB}")
        return
        
    os.makedirs(SOAPVOICE_DB_DIR, exist_ok=True)
    
    # Overwrite the git-lfs pointer file with a clean sqlite database file
    if os.path.exists(SOAPVOICE_DB):
        print(f"Removing old file placeholder at {SOAPVOICE_DB}...")
        os.remove(SOAPVOICE_DB)
        
    print(f"Creating new independent database at {SOAPVOICE_DB}...")
    dest_conn = sqlite3.connect(SOAPVOICE_DB)
    dest_cursor = dest_conn.cursor()
    
    # Attach clinic.db
    dest_cursor.execute(f"ATTACH DATABASE '{CLINIC_DB}' AS clinic")
    
    tables_to_copy = [
        "medical_nodes",
        "medical_edges",
        "disease_details",
        "medical_terminology",
        "case_templates",
        "medical_conditions",
        "medical_treatments",
        "medical_guidelines",
        "medical_knowledge"
    ]
    
    for table in tables_to_copy:
        print(f"Copying table '{table}' to independent database...")
        try:
            dest_cursor.execute(f"CREATE TABLE {table} AS SELECT * FROM clinic.{table}")
            print(f"  -> Cloned table '{table}'.")
        except Exception as e:
            print(f"Error copying table {table}: {e}")
            
    dest_conn.commit()
    dest_cursor.execute("DETACH DATABASE clinic")
    dest_conn.close()
    
    print("\nDatabase cloned successfully for independent use in SoapVoice!")

if __name__ == '__main__':
    copy_database()
