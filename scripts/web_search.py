import requests
import sys
import json

def search_tavily(query, api_key):
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 5
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"API request failed with status {response.status_code}", "details": response.text}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/web_search.py <query> <api_key>")
        sys.exit(1)
    
    query = sys.argv[1]
    api_key = sys.argv[2]
    results = search_tavily(query, api_key)
    print(json.dumps(results, indent=2, ensure_ascii=False))
