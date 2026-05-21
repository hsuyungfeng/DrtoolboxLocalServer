import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalLLM:
    def __init__(self, api_base="http://127.0.0.1:8080"):
        logger.info(f"Configuring remote LLM connection to {api_base}...")
        self.api_base = api_base
        self.llm = True # mock initialized state

    def generate(self, prompt, max_tokens=512, temperature=0.2):
        try:
            logger.info("Sending generation request to LLM server on 8080...")
            response = requests.post(
                f"{self.api_base}/v1/completions",
                json={
                    "model": "llama-qwen",
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                headers={"Content-Type": "application/json"},
                timeout=600
            )
            response.raise_for_status()
            data = response.json()
            # OpenAI compatible response format
            return data.get('choices', [{}])[0].get('text', '')
        except Exception as e:
            logger.error(f"LLM API request failed: {e}")
            return f"對不起，連接到本地 AI 模型時發生錯誤：{e}"

    def chat_generate(self, messages, max_tokens=1024, temperature=0.2):
        try:
            logger.info("Sending chat generation request to LLM server on 8080...")
            response = requests.post(
                f"{self.api_base}/v1/chat/completions",
                json={
                    "model": "llama-qwen",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                headers={"Content-Type": "application/json"},
                timeout=600
            )
            response.raise_for_status()
            data = response.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            logger.error(f"LLM API chat request failed: {e}")
            return f"對不起，連接到本地 AI 模型時發生錯誤：{e}"

# Singleton instance
llm_instance = LocalLLM()
