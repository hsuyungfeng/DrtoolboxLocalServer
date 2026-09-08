#!/usr/bin/env python3
import os
import sys
import requests
import json

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from src.rag_engine import RAGEngine

def main():
    rag = RAGEngine()
    query = "百日咳的症狀有哪些？"
    sql_context, pi_context, rag_context = rag._get_context(query, route="general")
    graph_raw = rag.graph_engine.query_graph_context(query)
    graph_context = graph_raw if graph_raw else "無相關醫學知識圖譜資料。"
    
    import datetime
    current_date = datetime.date.today()
    
    system_instruction = f"""你是一個專業的醫學與健康知識 AI 助理。今天是 {current_date}。
你可以結合「提供的參考資料」與你的「專業醫學知識庫」來回答使用者的健康問題。

【參考資料 (診所提供)】
{pi_context}
{rag_context}

【關聯參考資料 (知識圖譜)】
{graph_context}

【回答原則】
1. **結合知識**：如果參考資料中沒有提到，請使用你的專業醫學知識進行回答，確保資訊正確且有益。
2. **專業且繁體**：使用親切且專業的繁體中文回答.
3. **安全性**：提醒使用者你的建議僅供參考，若症狀持續應尋求醫師診斷。
4. **嚴禁報價**：絕對禁止提及 any 具體價格。"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": query}
    ]
    
    api_base = "http://127.0.0.1:8080"
    print("Sending POST request to /v1/chat/completions...")
    response = requests.post(
        f"{api_base}/v1/chat/completions",
        json={
            "model": "llama-qwen",
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.2
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print("Raw text response:")
        print(response.text[:2000])

if __name__ == "__main__":
    main()
