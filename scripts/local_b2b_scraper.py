import os
import sys
import sqlite3
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.openoutreach_bridge import OpenOutreachBridge, DB_PATH

logger = logging.getLogger(__name__)

# 預設 10 公里在地非診所商業目標類別
LOCAL_TARGET_CATEGORIES = [
    "健身房/健身工作室 (Gyms)",
    "瑜伽與普拉提會館 (Yoga & Pilates)",
    "科技公司/軟體園區 (Tech Firms)",
    "婚紗攝影/婚禮企劃 (Wedding Studios)",
    "高階美髮沙龍 (Hair Salons)",
    "企業福委會 (Corporate Welfare Committees)"
]

class LocalB2BScraper:
    """10km 地緣非診所店家/企業爬蟲，對接 Firecrawl 與洗庫至 b2b_leads"""

    def __init__(self, db_path: str = DB_PATH, firecrawl_url: str = "http://127.0.0.1:3002"):
        self.db_path = db_path
        self.firecrawl_url = firecrawl_url
        self.bridge = OpenOutreachBridge(db_path=db_path)

    def mock_mine_local_businesses(self, target_category: str = "Gyms", count: int = 3) -> List[Dict[str, Any]]:
        """模擬/發掘 10 公里在地企業店家並回傳結構化資料」"""
        samples = [
            {
                "company_id": f"gym_{target_category}_01",
                "company_name": f"極致極速健身會館 (10km 園區店)",
                "contact_email": "contact@fitmax10k.com.tw",
                "fb_page_url": "https://facebook.com/fitmax10k",
                "fb_messenger_url": "https://m.me/fitmax10k",
                "latest_post_url": "https://facebook.com/fitmax10k/posts/101",
                "category": target_category
            },
            {
                "company_id": f"yoga_{target_category}_02",
                "company_name": f"靜心瑜伽會館 (診所 5km)",
                "contact_email": "info@pureyoga5k.com",
                "fb_page_url": "https://facebook.com/pureyoga5k",
                "fb_messenger_url": "https://m.me/pureyoga5k",
                "latest_post_url": "https://facebook.com/pureyoga5k/posts/202",
                "category": target_category
            },
            {
                "company_id": f"tech_{target_category}_03",
                "company_name": f"智創科技股份有限公司福委會",
                "contact_email": "hr@smarttech.com.tw",
                "fb_page_url": "https://facebook.com/smarttech",
                "fb_messenger_url": "https://m.me/smarttech",
                "latest_post_url": "https://facebook.com/smarttech/posts/303",
                "category": target_category
            }
        ]
        return samples[:count]

    def run_ingestion(self, category: str = "Gyms", limit: int = 3) -> List[str]:
        """爬取並將資料洗入 clinic.db b2b_leads 資料表」"""
        leads = self.mock_mine_local_businesses(category, limit)
        tokens = []
        for lead in leads:
            token = self.bridge.add_full_lead(
                company_id=lead["company_id"],
                company_name=lead["company_name"],
                contact_email=lead.get("contact_email", ""),
                fb_page_url=lead.get("fb_page_url", ""),
                fb_messenger_url=lead.get("fb_messenger_url", ""),
                latest_post_url=lead.get("latest_post_url", ""),
                category=lead.get("category", category)
            )
            tokens.append(token)
            logger.info(f"✅ [Local B2B Scraper] 成功洗入 10km 在地目標: {lead['company_name']} -> Token: {token}")
        return tokens

if __name__ == "__main__":
    scraper = LocalB2BScraper()
    tokens = scraper.run_ingestion("Gyms", limit=3)
    print(f"--- 10km 在地企業爬蟲洗庫完成，產生 Tokens: {tokens} ---")
