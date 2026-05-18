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
                f"{self.api_base}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": max_tokens,
                    "temperature": temperature
                },
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            # llama.cpp server typically returns the generated text in 'content'
            return data.get('content', '')
        except Exception as e:
            logger.error(f"LLM API request failed: {e}")
            return f"對不起，連接到本地 AI 模型時發生錯誤：{e}"

# Singleton instance
llm_instance = LocalLLM()
