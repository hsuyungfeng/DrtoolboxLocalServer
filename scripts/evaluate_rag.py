import os
import sys
import json
import logging
import requests
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

import time

def evaluate():
    if not os.path.exists(GOLDEN_SET_PATH):
        logger.error(f"Golden set not found at {GOLDEN_SET_PATH}")
        return

    with open(GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
        golden_set = json.load(f)

    results = []
    total_score = 0

    print("\n" + "="*50)
    print("🚀 Starting RAG Golden Set Evaluation")
    print("="*50 + "\n")

    for entry in golden_set:
        qid = entry['id']
        question = entry['question']
        ground_truth = entry['ground_truth']
        criteria = entry['evaluation_criteria']
        
        print(f"[{qid}] Evaluating: {question}")
        
        # 1. Get AI Answer from the live system
        try:
            # Increased timeout to 180s for deep reasoning
            res = requests.post(CHAT_API_URL, json={"message": question, "user_id": "eval_bot"}, timeout=180)
            res.raise_for_status()
            ai_answer = res.json().get('reply', '')
        except Exception as e:
            logger.error(f"Failed to get AI answer for {qid}: {e}")
            ai_answer = f"ERROR: Could not get response. {e}"

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
5分：完全準確，包含所有關鍵點，語氣專業。
4分：準確且包含主要關鍵點，但有細微遺漏。
3分：部分準確，主要觀點有提到但細節不夠。
2分：嚴重不足，漏掉核心警訊或包含錯誤資訊。
1分：完全錯誤、包含敏感報價或與問題無關。

要求：請直接以 JSON 格式回傳評分結果，不要包含任何思考過程或額外說明。
格式範例：{{"score": 5, "reason": "說明理由"}}
"""
        try:
            judge_res_raw = llm_instance.generate(judge_prompt, max_tokens=300).strip()
            
            # Remove thinking tags
            if "<think>" in judge_res_raw:
                judge_res_raw = judge_res_raw.split("</think>")[-1].strip()
            
            # Handle markdown blocks
            if "```json" in judge_res_raw:
                judge_res_raw = judge_res_raw.split("```json")[1].split("```")[0].strip()
            elif "```" in judge_res_raw:
                judge_res_raw = judge_res_raw.split("```")[1].split("```")[0].strip()
            
            # Clean up trailing/leading junk
            judge_res_raw = judge_res_raw.strip()
            if not judge_res_raw.startswith("{"):
                # Try to find the first { and last }
                start = judge_res_raw.find("{")
                end = judge_res_raw.rfind("}")
                if start != -1 and end != -1:
                    judge_res_raw = judge_res_raw[start:end+1]
            
            judge_data = json.loads(judge_res_raw)
            score = int(judge_data.get('score', 0))
            reason = judge_data.get('reason', 'No reason provided.')
        except Exception as e:
            logger.error(f"Judge failed for {qid}: {e}. Raw response: {judge_res_raw if 'judge_res_raw' in locals() else 'N/A'}")
            score = 0
            reason = f"Judging Error: {e}"

        total_score += score
        results.append({
            "id": qid,
            "question": question,
            "ai_answer": ai_answer,
            "ground_truth": ground_truth,
            "score": score,
            "reason": reason
        })
        print(f"   -> Score: {score}/5 | Reason: {reason[:60]}...")
        
        # Small sleep to let GPU cool down
        time.sleep(2)

    # Final Report
    avg_score = total_score / len(golden_set) if golden_set else 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(REPORT_DIR, f"eval_report_{timestamp}.json")
    
    report = {
        "timestamp": timestamp,
        "average_score": avg_score,
        "detail_results": results
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

    print("\n" + "="*50)
    print(f"✅ Evaluation Complete!")
    print(f"📊 Average Score: {avg_score:.2f} / 5.00")
    print(f"📄 Report saved to: {report_file}")
    print("="*50 + "\n")

if __name__ == "__main__":
    evaluate()
