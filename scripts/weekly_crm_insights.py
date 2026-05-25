import os
import sys
import json
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_server import llm_instance
from config.settings import LOG_DIR, DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPORT_DIR = os.path.join(DATA_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

def generate_weekly_report():
    logger.info("Starting Weekly CRM Insights analysis...")
    
    # 1. Gather logs from the past 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    all_interactions = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        log_file = os.path.join(LOG_DIR, f"interactions_{date_str}.jsonl")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        all_interactions.append(json.loads(line))
        current += timedelta(days=1)

    if not all_interactions:
        logger.info("No interactions found for the past week. Skipping report.")
        return

    # 2. Prepare data for LLM analysis (summarize to fit context)
    # Extract only user prompts to save tokens
    prompts_summary = "\n".join([f"- {it['messages'][0]['content']}" for it in all_interactions[:100]])
    
    analysis_prompt = f"""你是一個專業的醫美診所經營顧問。請分析過去一週的病患對話內容，並產生一份「每週營運洞察報表」。

【病患對話提問摘要】
{prompts_summary}

【報表要求】
請提供繁體中文的專業分析，包含以下四大區塊：
1. **療程熱度榜**：本週被問最多的項目（如：皮秒、玻尿酸）及其詢問比例。
2. **病患痛點總結**：病患最擔心的問題（如：反黑、結節、疼痛、恢復期）。
3. **衛教缺口建議**：AI 回答不夠詳細或無法回答的問題，提醒醫師需要補上資料。
4. **營運建議**：根據本週趨勢，給予診所下週的行銷或服務優化建議。

請直接輸出 Markdown 格式。
"""
    
    try:
        report_md = llm_instance.generate(analysis_prompt, max_tokens=1500).strip()
        if "<think>" in report_md:
            report_md = report_md.split("</think>")[-1].strip()
            
        # 3. Save the report
        report_name = f"weekly_insights_{datetime.now().strftime('%Y%m%d')}.md"
        report_path = os.path.join(REPORT_DIR, report_name)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 緻妍外科診所 每週營運洞察報表\n")
            f.write(f"**生成日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**分析區間**: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}\n")
            f.write(f"**總對話數**: {len(all_interactions)} 筆\n\n")
            f.write(report_md)
            
        logger.info(f"Weekly report generated successfully: {report_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")

if __name__ == "__main__":
    generate_weekly_report()
