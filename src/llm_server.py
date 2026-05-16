from llama_cpp import Llama
from config.settings import MODEL_PATH
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalLLM:
    def __init__(self, model_path=MODEL_PATH):
        logger.info(f"Loading local model from {model_path}...")
        try:
            self.llm = Llama(
                model_path=model_path,
                n_gpu_layers=-1, # Offload all possible layers to GPU
                n_ctx=4096,      # Context window
                verbose=False
            )
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.llm = None

    def generate(self, prompt, max_tokens=512, temperature=0.2):
        if not self.llm:
            raise RuntimeError("LLM not initialized. Check model path and resources.")
            
        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False
        )
        return response['choices'][0]['text']

# Singleton instance
llm_instance = LocalLLM()
