import pytest
import sys
import os

# Ensure the root directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag_engine import RAGEngine

# Mock the LLM reasoning to return specific answers to test our post-processing
class MockReasoner:
    def __init__(self, mock_answer="這是一個測試回答。"):
        self.mock_answer = mock_answer

    def reason_chat(self, messages):
        return self.mock_answer

def test_otc_drug_localization():
    engine = RAGEngine()
    
    # Test Acetaminophen localization
    engine.reasoner = MockReasoner(mock_answer="您可以服用乙醯胺酚來退燒。")
    answer, _ = engine.query_integrated("我發燒了該怎麼辦？")
    assert "俗稱普拿疼的乙醯胺酚" in answer
    assert answer == "您可以服用俗稱普拿疼的乙醯胺酚來退燒。"
    
    # Test Ibuprofen localization
    engine.reasoner = MockReasoner(mock_answer="建議服用布洛芬止痛。")
    answer, _ = engine.query_integrated("牙齒很痛怎麼辦？")
    assert "常見的布洛芬" in answer
    assert answer == "建議服用常見的布洛芬止痛。"

def test_headache_cta_and_followup():
    engine = RAGEngine()
    
    engine.reasoner = MockReasoner(mock_answer="這可能是偏頭痛。")
    # Simulate headache query
    answer, _ = engine.query_integrated("我最近經常頭痛，該怎麼辦？")
    
    # Verify CTA was appended
    assert "建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。" in answer
    # Verify Interactive Follow-up was appended
    assert "若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！" in answer

def test_no_headache_cta_for_other_queries():
    engine = RAGEngine()
    
    engine.reasoner = MockReasoner(mock_answer="這可能是感冒。")
    # Simulate non-headache query
    answer, _ = engine.query_integrated("我感冒了該怎麼辦？")
    
    # Verify CTA is NOT appended for non-headache queries
    assert "預約門診" not in answer
    assert "補充頭痛的部位" not in answer
