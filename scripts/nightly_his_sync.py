import sqlite3
import os
import sys
import json
import logging
import tempfile
from datetime import datetime
from dbfread import DBF

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_sync_config():
    """Get HIS sync configuration including SMB credentials from database."""
    db_path = "data/db/clinic.db"
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM his_sync_config ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def sync_his_data():
    """
    Nightly sync: Abstract data from CO03L.DBF and update local DB.
    Supports local paths and SMB network shares.
    """
    config = get_sync_config()
    if not config:
        logger.error("❌ HIS Sync not configured.")
        return

    folder_path = config.get('folder_path', 'data')
    dbf_filename = "CO03L.DBF"
    is_smb = folder_path.startswith('//') or folder_path.startswith('\\\\')
    
    temp_dbf = None

    try:
        if is_smb:
            # ── SMB Network Share Logic ──
            logger.info(f"🌐 Accessing Network Share: {folder_path}")
            from smbclient import open_file, register_session
            
            # Clean up path for smbclient (needs to be \\server\share\path)
            # smbclient handles both / and \ but start with \\
            unc_path = folder_path.replace('/', '\\')
            if not unc_path.startswith('\\\\'):
                unc_path = '\\\\' + unc_path.lstrip('\\')
            
            server = unc_path.split('\\')[2]
            username = config.get('smb_username')
            password = config.get('smb_password')
            domain = config.get('smb_domain') or None

            if username and password:
                register_session(server, username=username, password=password, domain=domain)
                logger.info(f"✅ SMB Session registered for {server}")

            full_smb_path = os.path.join(unc_path, dbf_filename).replace('/', '\\')
            
            # Download DBF to a temporary file for dbfread to process
            temp_dbf = tempfile.NamedTemporaryFile(delete=False, suffix=".DBF")
            with open_file(full_smb_path, mode='rb') as smb_file:
                logger.info(f"📥 Downloading {dbf_filename} from network share...")
                temp_dbf.write(smb_file.read())
            temp_dbf.close()
            process_path = temp_dbf.name
        else:
            # ── Local Path Logic ──
            process_path = os.path.join(folder_path, dbf_filename)
            if not os.path.exists(process_path):
                logger.error(f"❌ Local HIS File not found: {process_path}")
                return
            logger.info(f"📂 Accessing Local File: {process_path}")

        # ── Data Abstraction Logic ──
        logger.info(f"🚀 Abstracting records from {dbf_filename}...")
        table = DBF(process_path, encoding='cp950', load=True)
        
        his_cache_db = "data/db/his.db"
        conn = sqlite3.connect(his_cache_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visit_records (
                patient_id TEXT,
                patient_name TEXT,
                visit_date TEXT,
                diagnosis TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        new_count = 0
        for record in table:
            # Common HIS headers for CO03L often look like this:
            pid = record.get('C0_PID', record.get('ID', ''))
            name = record.get('C0_NAME', record.get('NAME', ''))
            v_date = record.get('C0_DATE', record.get('DATE', ''))
            diag = record.get('C0_DIAG', record.get('DIAG', ''))
            
            if pid:
                cursor.execute("""
                    INSERT INTO visit_records (patient_id, patient_name, visit_date, diagnosis)
                    VALUES (?, ?, ?, ?)
                """, (pid, name, v_date, diag))
                new_count += 1
        
        conn.commit()
        conn.close()
        
        # Update Sync Status
        conn_clinic = sqlite3.connect("data/db/clinic.db")
        cursor_clinic = conn_clinic.cursor()
        cursor_clinic.execute("UPDATE his_sync_config SET last_sync = ?, status = 'success' WHERE folder_path = ?", 
                             (datetime.now().isoformat(), folder_path))
        conn_clinic.commit()
        conn_clinic.close()
        
        logger.info(f"✅ Sync complete. Abstracted {new_count} records to his.db")

    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Update failure status
        try:
            conn_clinic = sqlite3.connect("data/db/clinic.db")
            conn_clinic.execute("UPDATE his_sync_config SET status = 'failed' WHERE folder_path = ?", (folder_path,))
            conn_clinic.commit()
            conn_clinic.close()
        except: pass

    finally:
        # Clean up temporary file
        if temp_dbf and os.path.exists(temp_dbf.name):
            os.remove(temp_dbf.name)
            logger.info("🧹 Cleaned up temporary DBF file.")

if __name__ == "__main__":
    sync_his_data()
