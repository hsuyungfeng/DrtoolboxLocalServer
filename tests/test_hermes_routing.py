import pytest
import json
import os
from unittest.mock import patch, MagicMock
from src.api.app import create_app
from config.settings import LOG_DIR
from datetime import datetime

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('src.agent.hermes_router.llm_instance')
@patch('src.agent.hermes_router.RAGEngine')
def test_chat_routing_and_logging(mock_rag_class, mock_llm_instance, client):
    # Setup mocks
    mock_rag = mock_rag_class.return_value
    mock_rag.query.return_value = "This is a mock RAG response."
    mock_rag.query_integrated.return_value = "This is a mock RAG response."
    
    # Mock Hermes intent classification to return "special"
    mock_llm_instance.generate.return_value = "special"
    
    # Perform Request
    response = client.post('/api/chat/message', json={
        "user_id": "test_user_123",
        "message": "Tell me about the new skin treatment."
    })
    
    assert response.status_code == 200
    data = response.json
    assert data["reply"] == "This is a mock RAG response."
    assert data["route_used"] == "special"
    
    # Check that it called the correct integrated query
    mock_rag.query_integrated.assert_called_once_with("Tell me about the new skin treatment.")

    
    # Verify Logging
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"interactions_{date_str}.jsonl")
    
    assert os.path.exists(log_file)
    with open(log_file, 'r') as f:
        lines = f.readlines()
        last_log = json.loads(lines[-1])
        assert last_log["user_id"] == "test_user_123"
        assert last_log["metadata"]["route_used"] == "special"
        assert last_log["messages"][0]["content"] == "Tell me about the new skin treatment."
