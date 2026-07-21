import sqlite3
import os

def migrate_database():
    source_db = '/home/hsu/Desktop/SoapVoice/data/local_db/medical.db'
    target_db = '/home/hsu/Desktop/DrtoolboxLocalServer/data/db/clinic.db'

    print(f"Attaching {source_db} to {target_db}...")

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    try:
        cursor.execute(f"ATTACH DATABASE '{source_db}' AS soapvoice")
        
        tables_to_migrate = ['icd10_codes', 'drugs', 'medical_orders', 'case_templates']

        for table in tables_to_migrate:
            print(f"Migrating table: {table}...")
            
            # CRITICAL: Always use main. to avoid accidentally dropping from attached database
            cursor.execute(f"DROP TABLE IF EXISTS main.{table}")
            
            cursor.execute(f"SELECT sql FROM soapvoice.sqlite_master WHERE type='table' AND name='{table}'")
            schema_row = cursor.fetchone()
            
            if schema_row and schema_row[0]:
                schema = schema_row[0]
                # If schema has 'CREATE TABLE ', ensure it uses 'CREATE TABLE main.' to be absolutely safe
                # Note: This is a simplistic replacement, but since it's just 'CREATE TABLE table_name', it's okay.
                # Actually, CREATE TABLE without prefix naturally defaults to main, but let's be safe.
                cursor.execute(schema)
                # Copy data
                cursor.execute(f"INSERT INTO main.{table} SELECT * FROM soapvoice.{table}")
            else:
                cursor.execute(f"CREATE TABLE main.{table} AS SELECT * FROM soapvoice.{table}")
            
            # Verify count
            cursor.execute(f"SELECT COUNT(*) FROM main.{table}")
            count = cursor.fetchone()[0]
            print(f"  -> Successfully migrated {count} records to {table}.")

        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
