import pytest
import os
import sys
import sqlite3
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.openoutreach_bridge import OpenOutreachBridge, sanitize_email_prompt

def test_sanitize_email_prompt_no_price_leak():
    raw_prompt = "特別提供 NT$8000 原價 60000元的尊榮療程，只要 5000 元！"
    clean_prompt = sanitize_email_prompt(raw_prompt)
    
    assert "$8000" not in clean_prompt
    assert "60000元" not in clean_prompt
    assert "5000" not in clean_prompt
    assert "[貴賓專屬特約方案]" in clean_prompt or "[專案尊榮特惠]" in clean_prompt
    assert "嚴禁硬編碼具體療程金額" in clean_prompt

def test_b2b_bridge_lead_creation_and_analytics(tmp_path):
    test_db = str(tmp_path / "test_clinic.db")
    bridge = OpenOutreachBridge(db_path=test_db)
    
    token = bridge.add_lead("test_corp_10km", "測試 10 公里特約科技公司", "hr@test10km.com")
    assert token == "b2b_test_corp_10km"
    
    email_text = bridge.generate_outreach_email("測試 10 公里特約科技公司", token)
    assert "10 公里圈內" in email_text
    assert "utm_campaign=b2b_test_corp_10km" in email_text
    
    analytics = bridge.get_analytics()
    assert analytics["total_leads"] == 1
    assert len(analytics["top_leads"]) == 1
    assert analytics["top_leads"][0]["company_name"] == "測試 10 公里特約科技公司"
