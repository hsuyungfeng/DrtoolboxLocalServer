import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.services.message_router import route_message

class TestHighRiskNotification(unittest.TestCase):
    
    @patch('src.services.message_router._query_rag')
    @patch('src.services.message_router.notification_service.notify_high_risk')
    @patch('src.services.message_router.ConversationManager.save_message')
    @patch('src.services.line_responder.send_response')
    def test_high_risk_trigger(self, mock_send, mock_save, mock_notify, mock_rag):
        # Mock RAG to return high confidence but message contains high-risk keywords
        mock_rag.return_value = {"answer": "Some medical advice", "confidence": 0.9}
        mock_save.return_value = "msg-123"
        
        envelope = {
            "user_id": "U123456",
            "text": "醫生救命，我打完雷射後全臉紅腫，現在呼吸困難！",
            "reply_token": "token-abc",
            "received_at": "2026-06-01T12:00:00Z"
        }
        
        result = route_message(envelope)
        
        # Verify that notify_high_risk was called
        self.assertTrue(mock_notify.called)
        args, kwargs = mock_notify.call_args
        self.assertEqual(kwargs['patient_id'], "U123456")
        self.assertEqual(kwargs['risk_type'], "Symptom/Medical")
        self.assertIn("紅腫", kwargs['message'])
        
        print("✅ High-risk notification trigger verified.")

if __name__ == "__main__":
    unittest.main()
