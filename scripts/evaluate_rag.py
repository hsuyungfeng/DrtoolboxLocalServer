import os
import sys
import json
import logging
import requests
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_server import llm_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOLDEN_SET_PATH = "data/evaluation/golden_set.json"
REPORT_DIR = "data/evaluation/reports"
CHAT_API_URL = "http://127.0.0.1:5000/api/chat/message"

os.makedirs(REPORT_DIR, exist_ok=True)

def evaluate():
    if not os.path.exists(GOLDEN_SET_PATH):
        logger.error(f"Golden set not found at {GOLDEN_SET_PATH}")
        return

    with open(GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        golden_set = json.load(f)

    results = []
    total_score = 0
    total_latency = 0

    print("\n" + "="*60)
    print("🚀 Starting PageIndex / Reasoning RAG Evaluation")
    print("="*60 + "\n")

    for entry in golden_set:
        qid = entry['id']
        question = entry['question']
        ground_truth = entry['ground_truth']
        criteria = entry['evaluation_criteria']
        
        print(f"[{qid}] 📥 Question: {question}")
        
        # 1. Get AI Answer from the live system
        start_time = time.time()
        try:
            res = requests.post(CHAT_API_URL, json={"message": question, "user_id": "eval_bot"}, timeout=300)
            res.raise_for_status()
            data = res.json()
            ai_answer = data.get('reply', '')
            sys_confidence = data.get('confidence_score', 0)
            route = data.get('route_used', 'unknown')
        except Exception as e:
            logger.error(f"Failed to get AI answer for {qid}: {e}")
            ai_answer = f"ERROR: Could not get response. {e}"
            sys_confidence = 0
            route = "error"
        
        latency = time.time() - start_time
        total_latency += latency

        # 2. Use LLM as a Judge to score the answer
        judge_prompt = f"""你是一個專業的醫療 RAG 評測員。
請嚴格根據『標準答案』與『評分準則』，對『AI 回答』進行評分（1 到 5 分）。

【問題】
{question}

【標準答案（專家提供）】
{ground_truth}

【評分準則】
{criteria}

【AI 回答】
{ai_answer}

---
評分說明：
5分：完全準確，包含所有關鍵點，語氣專業，邏輯清晰。
4分：準確且包含主要關鍵點，但有細微遺漏或冗餘。
3分：部分準確，主要觀點有提到但細節不足或有輕微偏差。
2分：嚴重不足，漏掉核心警訊，或包含錯誤資訊。
1分：完全錯誤、包含敏感報價、答非所問或具備醫療風險。

要求：請直接以 JSON 格式回傳評分結果。
格式範例：{{"score": 5, "reason": "說明理由"}}
"""
        try:
            judge_res_raw = llm_instance.generate(judge_prompt, max_tokens=300).strip()
            
            # Remove thinking tags
            if "<think>" in judge_res_raw:
                judge_res_raw = judge_res_raw.split("</think>")[-1].strip()
            
            # Extract JSON block
            if "```json" in judge_res_raw:
                judge_res_raw = judge_res_raw.split("```json")[1].split("```")[0].strip()
            elif "```" in judge_res_raw:
                judge_res_raw = judge_res_raw.split("```")[1].split("```")[0].strip()
            
            start = judge_res_raw.find("{")
            end = judge_res_raw.rfind("}")
            if start != -1 and end != -1:
                judge_res_raw = judge_res_raw[start:end+1]
            
            judge_data = json.loads(judge_res_raw)
            score = int(judge_data.get('score', 0))
            reason = judge_data.get('reason', 'No reason provided.')
        except Exception as e:
            logger.error(f"Judge failed for {qid}: {e}")
            score = 0
            reason = f"Judging Error: {e}"

        total_score += score
        results.append({
            "id": qid,
            "question": question,
            "ai_answer": ai_answer,
            "ground_truth": ground_truth,
            "score": score,
            "reason": reason,
            "latency": round(latency, 2),
            "sys_confidence": sys_confidence,
            "route": route
        })
        print(f"   -> ⏱️ {latency:.2f}s | 🎯 Sys Confidence: {sys_confidence}% | ⭐ Judge: {score}/5")
        print(f"   -> 💬 Reason: {reason[:80]}...")
        
        time.sleep(1)

    # Final Stats
    count = len(golden_set)
    avg_score = total_score / count if count else 0
    avg_latency = total_latency / count if count else 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON Report
    json_report_file = os.path.join(REPORT_DIR, f"eval_report_{timestamp}.json")
    with open(json_report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_cases": count,
                "average_score": round(avg_score, 2),
                "average_latency": round(avg_latency, 2)
            },
            "results": results
        }, f, ensure_ascii=False, indent=4)

    # Generate Markdown Report
    md_report_file = os.path.join(REPORT_DIR, f"eval_report_{timestamp}.md")
    with open(md_report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Drtoolbox RAG Evaluation Report ({timestamp})\n\n")
        f.write(f"## 📊 Summary\n")
        f.write(f"- **Total Cases:** {count}\n")
        f.write(f"- **Average Judge Score:** {avg_score:.2f} / 5.00\n")
        f.write(f"- **Average Latency:** {avg_latency:.2f} seconds\n\n")
        
        f.write(f"## 📝 Detailed Results\n")
        f.write(f"| ID | Question | Score | Latency | Sys Conf | Route |\n")
        f.write(f"|---|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['id']} | {r['question']} | {r['score']}/5 | {r['latency']}s | {r['sys_confidence']}% | {r['route']} |\n")
        
        f.write(f"\n## 🔍 Content Analysis\n")
        for r in results:
            f.write(f"### [{r['id']}] {r['question']}\n")
            f.write(f"**AI Answer:**\n> {r['ai_answer']}\n\n")
            f.write(f"**Ground Truth:**\n> {r['ground_truth']}\n\n")
            f.write(f"**Judge Reason:** {r['reason']}\n\n")
            f.write(f"---\n")

    print("\n" + "="*60)
    print(f"✅ Evaluation Complete!")
    print(f"📊 Average Score: {avg_score:.2f} / 5.00")
    print(f"⏱️ Average Latency: {avg_latency:.2f}s")
    print(f"📄 MD Report: {md_report_file}")
    print("="*60 + "\n")

if __name__ == "__main__":
    evaluate()
