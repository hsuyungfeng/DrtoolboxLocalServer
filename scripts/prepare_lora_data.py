import os
import json
import logging
import argparse
from config.settings import LOG_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_to_alpaca(input_file, output_file):
    """Converts JSONL corrections to Alpaca format for instruction tuning."""
    alpaca_data = []
    
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                messages = data.get('messages', [])
                meta = data.get('metadata', {})
                route = meta.get('route', 'special')
                
                if len(messages) >= 2:
                    user_query = messages[0]['content']
                    ai_response = messages[1]['content']
                    
                    if route == "special":
                        instruction = "你是一個專業的診所助理，請根據診所準則回答。嚴禁報價，確保資訊來自診所內部資料。"
                    else:
                        instruction = "你是一個專業的醫學健康 AI 助理，請運用豐富的醫學知識提供專業且具備衛教價值的建議。"

                    alpaca_data.append({
                        "instruction": instruction,
                        "input": user_query,
                        "output": ai_response
                    })
            except Exception as e:
                logger.warning(f"Skipping malformed line: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=4)
    
    logger.info(f"✅ Converted {len(alpaca_data)} samples to Alpaca format: {output_file}")

def convert_to_sharegpt(input_file, output_file):
    """Converts JSONL corrections to ShareGPT format."""
    sharegpt_data = []
    
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                messages = data.get('messages', [])
                if len(messages) >= 2:
                    sharegpt_data.append({
                        "conversations": [
                            {"from": "human", "value": messages[0]['content']},
                            {"from": "gpt", "value": messages[1]['content']}
                        ]
                    })
            except Exception as e:
                logger.warning(f"Skipping malformed line: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sharegpt_data, f, ensure_ascii=False, indent=4)
    
    logger.info(f"✅ Converted {len(sharegpt_data)} samples to ShareGPT format: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare clinic data for LoRA fine-tuning.")
    parser.add_argument("--format", choices=["alpaca", "sharegpt"], default="alpaca", help="Target training format.")
    args = parser.parse_args()

    input_path = os.path.join(LOG_DIR, "verified_training_data.jsonl")
    output_path = os.path.join(LOG_DIR, f"training_data_{args.format}.json")
    
    if args.format == "alpaca":
        convert_to_alpaca(input_path, output_path)
    else:
        convert_to_sharegpt(input_path, output_path)
