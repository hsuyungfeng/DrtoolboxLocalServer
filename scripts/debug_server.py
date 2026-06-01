import os
import sys
import threading
import time
import requests

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.app import create_app

def run_server():
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    print("Waiting for server to start...")
    time.sleep(10)
    
    try:
        res = requests.get("http://127.0.0.1:5000/health", timeout=5)
        print(f"Health check status: {res.status_code}")
        print(f"Health check body: {res.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

    print("Checking specific route...")
    try:
        res = requests.post("http://127.0.0.1:5000/api/v1/curation/suggest_correction", 
                           json={"prompt": "test"}, 
                           headers={"X-Staff-ID": "staff-001"},
                           timeout=10)
        print(f"Route check status: {res.status_code}")
        print(f"Route check body: {res.text}")
    except Exception as e:
        print(f"Route check failed: {e}")
