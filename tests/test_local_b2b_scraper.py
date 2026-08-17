import pytest
import os
import sqlite3
import tempfile
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.openoutreach_bridge import OpenOutreachBridge, init_b2b_tables
from scripts.local_b2b_scraper import LocalB2BScraper

def test_b2b_schema_expansion():
    """驗證 b2b_leads 多渠道欄位擴充與完整建立"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
        
    try:
        init_b2b_tables(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(b2b_leads);")
        cols = [c[1] for c in cursor.fetchall()]
        conn.close()
        
        for expected in ['fb_page_url', 'fb_messenger_url', 'latest_post_url', 'category', 'outreach_channel']:
            assert expected in cols, f"Missing expected column: {expected}"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_local_b2b_scraper_ingestion():
    """驗證 10km 在地店家爬蟲洗庫流程"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
        
    try:
        scraper = LocalB2BScraper(db_path=db_path)
        res = scraper.run_ingestion(category="Gyms", limit=2)
        tokens = res["tokens"]
        assert len(tokens) == 2
        assert tokens[0].startswith("b2b_")
        
        bridge = OpenOutreachBridge(db_path=db_path)
        analytics = bridge.get_analytics()
        assert analytics["total_leads"] == 2
        assert analytics["top_leads"][0]["category"] == "Gyms"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_multi_channel_dispatch():
    """驗證 Email -> Messenger -> Comment 三階渠道自動派遣邏輯"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
        
    try:
        bridge = OpenOutreachBridge(db_path=db_path)
        
        # Lead 1: Email present
        bridge.add_full_lead(company_id="corp_email", company_name="Email Corp", contact_email="test@corp.com")
        res1 = bridge.dispatch_multi_channel_outreach("corp_email")
        assert res1["sent_channel"] == "email"
        
        # Lead 2: FB Messenger present, no email
        bridge.add_full_lead(company_id="corp_msg", company_name="Msg Gym", fb_messenger_url="https://m.me/msggym")
        res2 = bridge.dispatch_multi_channel_outreach("corp_msg")
        assert res2["sent_channel"] == "messenger"
        
        # Lead 3: Latest Post URL present, no email/messenger
        bridge.add_full_lead(company_id="corp_post", company_name="Post Studio", latest_post_url="https://facebook.com/post/101")
        res3 = bridge.dispatch_multi_channel_outreach("corp_post")
        assert res3["sent_channel"] == "post_comment"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
