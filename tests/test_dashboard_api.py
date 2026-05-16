import pytest
from src.api.app import create_app
import json

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_logs(client):
    response = client.get('/api/dashboard/logs')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_save_correction(client):
    mock_log = {
        "timestamp": "2026-05-16T00:00:00Z",
        "user_id": "test_user",
        "messages": [
            {"role": "user", "content": "What is the clinic address?"},
            {"role": "assistant", "content": "We are located at Mars."}
        ],
        "metadata": {"route_used": "special", "context_nodes": []}
    }
    
    response = client.post('/api/dashboard/logs/correct', json={
        "original_log": mock_log,
        "corrected_response": "We are located in Taipei."
    })
    
    assert response.status_code == 200
    assert response.json["status"] == "success"
