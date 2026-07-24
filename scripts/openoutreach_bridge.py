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
    
    # 2. 擴充 b2b_leads 表 (多渠道支援)
    cursor.execute("PRAGMA table_info(b2b_leads);")
    b2b_cols = [col[1] for col in cursor.fetchall()]
    new_b2b_columns = {
        'fb_page_url': 'TEXT',
        'fb_messenger_url': 'TEXT',
        'latest_post_url': 'TEXT',
        'category': 'TEXT',
        'outreach_channel': 'TEXT'
    }
    for col_name, col_type in new_b2b_columns.items():
        if col_name not in b2b_cols:
            cursor.execute(f"ALTER TABLE b2b_leads ADD COLUMN {col_name} {col_type};")

    # 3. 擴充 patients 表 (如未存在 b2b_company_id 欄位)
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
    logger.info("✅ B2B Leads Database multi-channel schema initialized successfully.")

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
        return self.add_full_lead(company_id=company_id, company_name=company_name, contact_email=contact_email)

    def add_full_lead(self, company_id: str, company_name: str, contact_email: str = "", 
                      fb_page_url: str = "", fb_messenger_url: str = "", 
                      latest_post_url: str = "", category: str = "Corporate") -> str:
        """新增或更新多渠道地推潛在店家/企業"""
        utm_token = f"b2b_{company_id}"
        
        # 自動判定最佳接觸管道
        if contact_email and "@" in contact_email:
            preferred_channel = "email"
        elif fb_messenger_url:
            preferred_channel = "messenger"
        elif latest_post_url or fb_page_url:
            preferred_channel = "post_comment"
        else:
            preferred_channel = "email"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO b2b_leads (
                company_id, company_name, contact_email, utm_token,
                fb_page_url, fb_messenger_url, latest_post_url, category, outreach_channel
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                company_name=excluded.company_name,
                contact_email=excluded.contact_email,
                fb_page_url=excluded.fb_page_url,
                fb_messenger_url=excluded.fb_messenger_url,
                latest_post_url=excluded.latest_post_url,
                category=excluded.category,
                outreach_channel=excluded.outreach_channel,
                updated_at=CURRENT_TIMESTAMP;
        """, (company_id, company_name, contact_email, utm_token, 
              fb_page_url, fb_messenger_url, latest_post_url, category, preferred_channel))
        conn.commit()
        conn.close()
        return utm_token

    def dispatch_multi_channel_outreach(self, company_id: str) -> Dict[str, Any]:
        """根據優先管道發送開拓訊息 (Tier 1 Email -> Tier 2 Messenger -> Tier 3 Comment)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT company_name, contact_email, utm_token, fb_page_url, fb_messenger_url, latest_post_url, outreach_channel
            FROM b2b_leads WHERE company_id = ?;
        """, (company_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": "Company not found"}

        company_name, contact_email, utm_token, fb_page, fb_msg, latest_post, channel = row
        line_url = f"https://line.me/R/ti/p/@zhiyan?utm_source=b2b_multi&utm_campaign={utm_token}"
        
        sent_channel = None
        # Priority 1: Email
        if contact_email and "@" in contact_email:
            sent_channel = "email"
            self.send_outreach_email(company_id)
        # Priority 2: Messenger
        elif fb_msg or fb_page:
            sent_channel = "messenger"
            logger.info(f"💬 [Messenger Agent] 發送開拓卡片至 {company_name} ({fb_msg or fb_page}) -> LINE: {line_url}")
            cursor.execute("UPDATE b2b_leads SET status='emailed', emails_sent=emails_sent+1 WHERE company_id=?;", (company_id,))
            conn.commit()
        # Priority 3: FB Post Comment
        elif latest_post:
            sent_channel = "post_comment"
            logger.info(f"💬 [FB Post Comment Agent] 於最新貼文留言 {latest_post} 邀請合作 -> LINE: {line_url}")
            cursor.execute("UPDATE b2b_leads SET status='emailed', emails_sent=emails_sent+1 WHERE company_id=?;", (company_id,))
            conn.commit()
        else:
            sent_channel = "email"
            self.send_outreach_email(company_id)

        conn.close()
        return {"success": True, "company_id": company_id, "sent_channel": sent_channel, "line_url": line_url}

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

    def send_outreach_email(self, company_id: str, email_body: Optional[str] = None) -> bool:
        """實體寄送/對接 OpenOutreach SMTP 發信並更新紀錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. 取得企業資料
        cursor.execute("SELECT company_name, contact_email, utm_token FROM b2b_leads WHERE company_id = ?;", (company_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
            
        company_name, contact_email, utm_token = row
        if not email_body:
            email_body = self.generate_outreach_email(company_name, utm_token)
            
        # 2. 如果設定有 SMTP (例如利用 python smtplib 或 OpenOutreach API 發信)
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        
        sent_success = False
        if smtp_host and smtp_user and smtp_pass and contact_email:
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText(email_body, 'plain', 'utf-8')
                msg['Subject'] = f"【緻妍診所】VIP 企業特約合作邀請 - {company_name}"
                msg['From'] = smtp_user
                msg['To'] = contact_email
                
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                logger.info(f"📧 成功發送特約開拓信件至 {contact_email}")
                sent_success = True
            except Exception as mail_err:
                logger.error(f"SMTP 發信失敗: {mail_err}")
                sent_success = False
        else:
            # 模擬 / 記錄發信觸發
            logger.info(f"⚡ [Auto-Outreach Simulator] 已為 {company_name} ({contact_email}) 觸發 OpenOutreach 開拓推播")
            sent_success = True
            
        # 3. 更新數據庫中的信件寄送計數
        if sent_success:
            cursor.execute("""
                UPDATE b2b_leads 
                SET emails_sent = emails_sent + 1, status = 'emailed', updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?;
            """, (company_id,))
            conn.commit()
            
        conn.close()
        return sent_success

    def get_analytics(self) -> Dict[str, Any]:
        """讀取 B2B 轉化漏斗數據"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(emails_sent), SUM(line_linked_count) FROM b2b_leads;")
        total_leads, total_sent, total_linked = cursor.fetchone()
        
        cursor.execute("""
            SELECT b.company_name, b.company_id, b.emails_sent, b.line_linked_count, b.status,
                   COALESCE(b.category, 'Corporate'), COALESCE(b.outreach_channel, 'email'),
                   b.contact_email, b.fb_messenger_url, b.latest_post_url, b.fb_page_url
            FROM b2b_leads b ORDER BY b.line_linked_count DESC, b.created_at DESC LIMIT 50;
        """)
        top_leads = [
            {
                "company_name": row[0],
                "company_id": row[1],
                "emails_sent": row[2] or 0,
                "line_linked_count": row[3] or 0,
                "status": row[4],
                "category": row[5],
                "outreach_channel": row[6],
                "contact_email": row[7] or "",
                "fb_messenger_url": row[8] or "",
                "latest_post_url": row[9] or "",
                "fb_page_url": row[10] or ""
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
