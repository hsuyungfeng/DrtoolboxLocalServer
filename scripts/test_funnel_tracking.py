import sys
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import logging
logging.basicConfig(level=logging.INFO)

# Force DATA_DIR for test
os.environ["DATA_DIR"] = "data"
# Mock LINE credentials so WebhookHandler doesn't fail
os.environ["LINE_CHANNEL_SECRET"] = "dummy_secret"

# Mock LINE Bot API but NOT WebhookHandler to prevent replacing functions with mocks
with patch('linebot.LineBotApi'):
    from src.api.routes.webhook import handle_postback, CONVERSIONS_LOG_FILE, log_conversion

class MockEvent:
    def __init__(self, user_id, data, reply_token):
        self.source = MagicMock()
        self.source.user_id = user_id
        self.postback = MagicMock()
        self.postback.data = data
        self.reply_token = reply_token

def test_conversion_tracking():
    print(f"🚀 Testing Marketing Funnel Tracking... (Log Path: {CONVERSIONS_LOG_FILE})")
    
    user_id = "U_TEST_CONVERSION"
    treatment = "pico"
    data = f"action=booking&treatment={treatment}"
    reply_token = "test_reply_token"
    
    event = MockEvent(user_id, data, reply_token)
    
    # Ensure log file is clean for test
    if os.path.exists(CONVERSIONS_LOG_FILE):
        os.remove(CONVERSIONS_LOG_FILE)
    
    # Call the handler with mocked dependencies
    with patch('src.api.routes.webhook.line_bot_api') as mock_line:
        # We need to make sure the mocked line_bot_api is treated as True in the 'if line_bot_api:' check
        # But in Python, a MagicMock is always truthy.
        
        handle_postback(event)
        
        # Verify LINE reply was called
        print(f"✅ LINE Reply calls: {mock_line.reply_message.call_count}")
        
    # Verify Log File
    if os.path.exists(CONVERSIONS_LOG_FILE):
        with open(CONVERSIONS_LOG_FILE, 'r') as f:
            line = f.readline()
            if not line:
                print("❌ Log file is empty!")
                sys.exit(1)
            log_entry = json.loads(line)
            print(f"✅ Log Entry Found: {log_entry}")
            assert log_entry['user_id'] == user_id
            assert log_entry['treatment'] == treatment
            assert log_entry['event'] == 'booking_click'
    else:
        print(f"❌ Log file was not created at {CONVERSIONS_LOG_FILE}!")
        # Try manual log to see if permissions are an issue
        try:
            log_conversion(user_id, treatment)
            if os.path.exists(CONVERSIONS_LOG_FILE):
                print("⚠️ Manual log worked, but handle_postback failed.")
        except Exception as e:
            print(f"❌ Manual log also failed: {e}")
        sys.exit(1)

    print("🎉 Funnel Tracking Test Passed!")

if __name__ == "__main__":
    test_conversion_tracking()
