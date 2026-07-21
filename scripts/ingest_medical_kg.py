import os
import json
import sqlite3
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'db', 'clinic.db')
SOURCE_JSON = '/tmp/medical_kg_eval/chatbot-base-on-Knowledge-Graph/data/medical.json'

def init_db(conn):
    cursor = conn.cursor()
    # Create the main table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disease_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            desc TEXT,
            category TEXT,
            prevent TEXT,
            cause TEXT,
            symptom TEXT,
            yibao_status TEXT,
            get_prob TEXT,
            easy_get TEXT,
            get_way TEXT,
            acompany TEXT,
            cure_department TEXT,
            cure_way TEXT,
            cure_lasttime TEXT,
            cured_prob TEXT,
            common_drug TEXT,
            cost_money TEXT,
            check_items TEXT,
            do_eat TEXT,
            not_eat TEXT,
            recommand_eat TEXT,
            recommand_drug TEXT,
            drug_detail TEXT
        )
    ''')

    # Create FTS5 virtual table for fast full-text search
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS disease_knowledge_fts USING fts5(
            name, desc, symptom, prevent, cause, common_drug,
            content='disease_knowledge', content_rowid='id'
        )
    ''')

    # Triggers to keep FTS table updated
    cursor.executescript('''
        CREATE TRIGGER IF NOT EXISTS disease_knowledge_ai AFTER INSERT ON disease_knowledge BEGIN
            INSERT INTO disease_knowledge_fts(rowid, name, desc, symptom, prevent, cause, common_drug)
            VALUES (new.id, new.name, new.desc, new.symptom, new.prevent, new.cause, new.common_drug);
        END;
        CREATE TRIGGER IF NOT EXISTS disease_knowledge_ad AFTER DELETE ON disease_knowledge BEGIN
            INSERT INTO disease_knowledge_fts(disease_knowledge_fts, rowid, name, desc, symptom, prevent, cause, common_drug)
            VALUES ('delete', old.id, old.name, old.desc, old.symptom, old.prevent, old.cause, old.common_drug);
        END;
        CREATE TRIGGER IF NOT EXISTS disease_knowledge_au AFTER UPDATE ON disease_knowledge BEGIN
            INSERT INTO disease_knowledge_fts(disease_knowledge_fts, rowid, name, desc, symptom, prevent, cause, common_drug)
            VALUES ('delete', old.id, old.name, old.desc, old.symptom, old.prevent, old.cause, old.common_drug);
            INSERT INTO disease_knowledge_fts(rowid, name, desc, symptom, prevent, cause, common_drug)
            VALUES (new.id, new.name, new.desc, new.symptom, new.prevent, new.cause, new.common_drug);
        END;
    ''')
    conn.commit()

def process_file():
    if not os.path.exists(SOURCE_JSON):
        logging.error(f"Source file not found: {SOURCE_JSON}")
        sys.exit(1)
        
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cursor = conn.cursor()

    success_count = 0
    error_count = 0

    with open(SOURCE_JSON, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                
                # Helper to convert list to json string
                def to_json(key):
                    val = data.get(key)
                    if isinstance(val, list):
                        return json.dumps(val, ensure_ascii=False)
                    elif val is None:
                        return None
                    return str(val)

                name = data.get('name')
                if not name:
                    continue

                cursor.execute('''
                    INSERT OR IGNORE INTO disease_knowledge (
                        name, desc, category, prevent, cause, symptom, yibao_status,
                        get_prob, easy_get, get_way, acompany, cure_department, cure_way,
                        cure_lasttime, cured_prob, common_drug, cost_money, check_items,
                        do_eat, not_eat, recommand_eat, recommand_drug, drug_detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name,
                    data.get('desc'),
                    to_json('category'),
                    data.get('prevent'),
                    data.get('cause'),
                    to_json('symptom'),
                    data.get('yibao_status'),
                    data.get('get_prob'),
                    data.get('easy_get'),
                    data.get('get_way'),
                    to_json('acompany'),
                    to_json('cure_department'),
                    to_json('cure_way'),
                    data.get('cure_lasttime'),
                    data.get('cured_prob'),
                    to_json('common_drug'),
                    data.get('cost_money'),
                    to_json('check'),
                    to_json('do_eat'),
                    to_json('not_eat'),
                    to_json('recommand_eat'),
                    to_json('recommand_drug'),
                    to_json('drug_detail')
                ))
                success_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"Error parsing line: {e}")

    conn.commit()
    conn.close()
    
    logging.info(f"Ingestion complete! Successfully imported {success_count} diseases. Errors: {error_count}")

if __name__ == "__main__":
    process_file()
