#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Script for Medical Knowledge Graph
Migrates JSONL data to local SQLite.
"""

import os
import json
import sqlite3
import sys

# Define database path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, 'data', 'db', 'clinic.db')
JSON_PATH = os.path.join(PROJECT_DIR, 'chatbot-base-on-Knowledge-Graph', 'data', 'medical.json')

def setup_db(conn):
    """Create schema tables for medical graph nodes and edges."""
    cursor = conn.cursor()
    
    # Drop existing tables if they exist to avoid stale data (for fresh migration)
    cursor.execute("DROP TABLE IF EXISTS disease_details")
    cursor.execute("DROP TABLE IF EXISTS medical_edges")
    cursor.execute("DROP TABLE IF EXISTS medical_nodes")
    
    # Create medical nodes table
    cursor.execute("""
    CREATE TABLE medical_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL
    )
    """)
    
    # Create medical edges table
    cursor.execute("""
    CREATE TABLE medical_edges (
        source_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        relation TEXT NOT NULL,
        PRIMARY KEY (source_id, target_id, relation),
        FOREIGN KEY (source_id) REFERENCES medical_nodes(id) ON DELETE CASCADE,
        FOREIGN KEY (target_id) REFERENCES medical_nodes(id) ON DELETE CASCADE
    )
    """)
    
    # Create disease details table
    cursor.execute("""
    CREATE TABLE disease_details (
        node_id INTEGER PRIMARY KEY,
        description TEXT,
        cause TEXT,
        prevent TEXT,
        cure_lasttime TEXT,
        cured_prob TEXT,
        FOREIGN KEY (node_id) REFERENCES medical_nodes(id) ON DELETE CASCADE
    )
    """)
    
    # Build indexes for fast retrieval
    cursor.execute("CREATE INDEX idx_nodes_name ON medical_nodes(name)")
    cursor.execute("CREATE INDEX idx_nodes_label ON medical_nodes(label)")
    cursor.execute("CREATE INDEX idx_edges_source ON medical_edges(source_id)")
    cursor.execute("CREATE INDEX idx_edges_target ON medical_edges(target_id)")
    cursor.execute("CREATE INDEX idx_edges_relation ON medical_edges(relation)")
    
    conn.commit()
    print("Database schema initialized successfully.")

def migrate():
    if not os.path.exists(JSON_PATH):
        print(f"Error: Source file not found at {JSON_PATH}", file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    
    cursor = conn.cursor()
    
    # Memory cache to keep track of name -> node_id mapping to avoid redundant db inserts/lookups
    node_cache = {}
    
    def get_or_create_node(name, label):
        name = name.strip()
        if not name:
            return None
        if name in node_cache:
            return node_cache[name]
        
        # Try to insert
        try:
            cursor.execute("INSERT INTO medical_nodes (name, label) VALUES (?, ?)", (name, label))
            node_id = cursor.lastrowid
            node_cache[name] = node_id
            return node_id
        except sqlite3.IntegrityError:
            # If already exists in DB but not in cache
            cursor.execute("SELECT id FROM medical_nodes WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                node_id = row[0]
                node_cache[name] = node_id
                return node_id
            return None

    print("Beginning migration. Reading JSON line by line...")
    
    count = 0
    edge_count = 0
    
    # Load all records into memory first if file is small, or parse line-by-line
    # 45MB is small enough to load/parse efficiently
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            try:
                record = json.loads(line)
            except Exception as e:
                print(f"Error parsing JSON on line {count+1}: {e}")
                continue
                
            disease_name = record.get("name")
            if not disease_name:
                continue
                
            # Create disease node
            disease_id = get_or_create_node(disease_name, "Disease")
            if not disease_id:
                continue
                
            # Insert details
            cursor.execute("""
            INSERT OR REPLACE INTO disease_details (node_id, description, cause, prevent, cure_lasttime, cured_prob)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                disease_id,
                record.get("desc"),
                record.get("cause"),
                record.get("prevent"),
                record.get("cure_lasttime"),
                record.get("cured_prob")
            ))
            
            # Helper to link list of entities with a relationship type
            def add_relations(items, target_label, relation_type):
                nonlocal edge_count
                if not items:
                    return
                # Ensure it is a list
                if isinstance(items, str):
                    items = [items]
                for item in items:
                    if not isinstance(item, str):
                        continue
                    item = item.strip()
                    if not item:
                        continue
                    target_id = get_or_create_node(item, target_label)
                    if target_id:
                        try:
                            cursor.execute(
                                "INSERT OR IGNORE INTO medical_edges (source_id, target_id, relation) VALUES (?, ?, ?)",
                                (disease_id, target_id, relation_type)
                            )
                            edge_count += 1
                        except Exception:
                            pass
            
            # Map arrays to relationships
            add_relations(record.get("symptom"), "Symptom", "has_symptom")
            add_relations(record.get("acompany"), "Disease", "acompany_with")
            add_relations(record.get("recommand_drug"), "Drug", "recommand_drug")
            add_relations(record.get("common_drug"), "Drug", "common_drug")
            add_relations(record.get("check"), "Check", "need_check")
            add_relations(record.get("do_eat"), "Food", "do_eat")
            add_relations(record.get("no_eat"), "Food", "no_eat")
            add_relations(record.get("recommand_eat"), "Food", "recommand_eat")
            
            count += 1
            if count % 1000 == 0:
                conn.commit()
                print(f"Processed {count} diseases... ({len(node_cache)} nodes, {edge_count} edges inserted)")
                
    conn.commit()
    conn.close()
    
    print("\nMigration Completed Successfully!")
    print(f"Total Diseases Processed: {count}")
    print(f"Total Cached Nodes: {len(node_cache)}")
    print(f"Total Edges Inserted: {edge_count}")

if __name__ == '__main__':
    migrate()
