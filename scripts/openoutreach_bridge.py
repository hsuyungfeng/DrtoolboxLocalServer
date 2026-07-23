import os
import sqlite3
import json
import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
DB_PATH = os.path.join(DATA_DIR, 'db', 'clinic.db')

def init_b2b_tables(db_path: str = DB_PATH):
    """初始化 clinic.db 中的 b2b_leads 表與擴充 patients 表"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 建立 b2b_leads 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS b2b_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            utm_token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'discovered', -- discovered, emailed, opened, linked, converted
            emails_sent INTEGER DEFAULT 0,
            line_linked_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # 2. 擴充 patients 表 (如未存在 b2b_company_id 欄位)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT,
            dob TEXT,
            mrn TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("PRAGMA table_info(patients);")
    columns = [col[1] for col in cursor.fetchall()]
    if 'b2b_company_id' not in columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN b2b_company_id TEXT;")
    if 'tags' not in columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN tags TEXT;")
        
    conn.commit()
    conn.close()
    logger.info("✅ B2B Leads Database schema initialized successfully.")

def sanitize_email_prompt(prompt_text: str) -> str:
    """
    AGENTS.md 嚴格價格防禦機制：
    遮蔽與過濾任何具體金額 (例如 $8000, 60000元等)，防止 OpenOutreach 外發信件洩漏價格。
    """
    # 判讀並替換 $8000, 60000元, NT$5000 等價格字樣
    sanitized = re.sub(r'(\$|NT\$|NTD\s?)\s?\d+([,.]\d+)?', '[貴賓專屬特約方案]', prompt_text)
    sanitized = re.sub(r'\d+\s*(元|萬|塊)', '[專案尊榮特惠]', sanitized)
    
    # 補加上導引聲明
    strict_clause = (
        "\n\n[系統規範提示：本診所遵循醫療合規指引，信件中嚴禁硬編碼具體療程金額。"
        "請引導貴賓掃描下方 LINE 官方帳號 QR Code 或聯繫診所專人索取最新特約合作簡章。]"
    )
    return sanitized + strict_clause

class OpenOutreachBridge:
    """Bridge for syncing B2B leads from OpenOutreach to DrtoolboxLocalServer clinic.db"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_b2b_tables(self.db_path)
        
    def add_lead(self, company_id: str, company_name: str, contact_email: str) -> str:
        """新增或更新地推潛在企業"""
        utm_token = f"b2b_{company_id}"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO b2b_leads (company_id, company_name, contact_email, utm_token)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                company_name=excluded.company_name,
                contact_email=excluded.contact_email,
                updated_at=CURRENT_TIMESTAMP;
        """, (company_id, company_name, contact_email, utm_token))
        conn.commit()
        conn.close()
        return utm_token

    def generate_outreach_email(self, company_name: str, utm_token: str) -> str:
        """產生無價格洩漏、附帶 UTM LINE 綁定連結的合規開拓信件」"""
        line_url = f"https://line.me/R/ti/p/@zhiyan?utm_source=b2b_email&utm_campaign={utm_token}"
        
        raw_template = f"""尊敬的 {company_name} 福委會與 HR 團隊您好：

緻妍診所 (Zhiyan Aesthetic Clinic) 誠摯邀請貴公司成為我們的 VIP 尊榮特約合作夥伴！
我們為診所周邊 10 公里圈內之優質企業與合作單位提供專業的員工身心舒壓、肌膚健康檢測與尊榮特約保健照護服務。

🎁 貴公司員工專屬權益：
- 憑員工證或專屬 LINE 綁定即可享有 VIP 專屬折扣與諮詢綠色通道。
- 專人提供一對一抗衰與肌膚保養諮詢服務。

請透過下方連結加入緻妍診所官方 LINE 完成特約身份綁定：
👉 點擊綁定企業 VIP 權益: {line_url}

我們亦提供企業內部紓壓與健康保養講座，歡迎回信或聯繫專人索取特約簡章！

緻妍診所 敬上"""

        return sanitize_email_prompt(raw_template)

    def get_analytics(self) -> Dict[str, Any]:
        """讀取 B2B 轉化漏斗數據"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(emails_sent), SUM(line_linked_count) FROM b2b_leads;")
        total_leads, total_sent, total_linked = cursor.fetchone()
        
        cursor.execute("""
            SELECT b.company_name, b.company_id, b.emails_sent, b.line_linked_count, b.status
            FROM b2b_leads b ORDER BY b.line_linked_count DESC LIMIT 10;
        """)
        top_leads = [
            {
                "company_name": row[0],
                "company_id": row[1],
                "emails_sent": row[2] or 0,
                "line_linked_count": row[3] or 0,
                "status": row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return {
            "total_leads": total_leads or 0,
            "total_emails_sent": total_sent or 0,
            "total_line_linked": total_linked or 0,
            "top_leads": top_leads
        }

if __name__ == "__main__":
    bridge = OpenOutreachBridge()
    token = bridge.add_lead("tech_corp_01", "竹科特約科技股份有限公司", "hr@techcorp.com.tw")
    email_content = bridge.generate_outreach_email("竹科特約科技股份有限公司", token)
    print("--- 產出合規 B2B Outreach 信件範例 ---")
    print(email_content)
    print("\n--- B2B Analytics ROI ---")
    print(bridge.get_analytics())
