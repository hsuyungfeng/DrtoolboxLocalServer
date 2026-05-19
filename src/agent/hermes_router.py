import logging
from src.rag_engine import RAGEngine
from src.llm_server import llm_instance

logger = logging.getLogger(__name__)

class HermesRouter:
    """Simulates Hermes agent tool routing logic for Local LLM."""
    def __init__(self):
        self.rag = RAGEngine()
        self.llm = llm_instance
        
        # Ingest the data into PageIndex in the background so it doesn't freeze the server
        import threading
        def background_ingest():
            from src.data_loader import get_special_data, get_general_data
            logger.info("Starting fast data ingestion from existing .txt files...")
            special_docs = get_special_data(self.rag)
            if special_docs:
                self.rag.ingest_special_data(special_docs)
            general_docs = get_general_data(self.rag)
            if general_docs:
                self.rag.ingest_general_data(general_docs)
            logger.info(f"Fast data ingestion complete! (Loaded {len(special_docs)} special docs, {len(general_docs)} general docs)")
            
        threading.Thread(target=background_ingest, daemon=True).start()
        
    def determine_route(self, prompt: str) -> str:
        """
        Uses the local LLM (or a heuristic) to determine whether to query 
        Clinic Special Data or General Medical Knowledge.
        """
        # A simple router prompt to emulate Hermes tool selection
        router_prompt = f"""<|im_start|>system
You are a routing agent for a clinic. Decide if the user's query is about "Clinic Special Marketing/Procedures" (reply 'special') or "General Medical Knowledge" (reply 'general'). Reply with only one word.
<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
"""
        try:
            response = self.llm.generate(router_prompt, max_tokens=10).strip().lower()
            if "special" in response:
                return "special"
            return "general"
        except Exception as e:
            logger.warning(f"Routing LLM failed, defaulting to general: {e}")
            return "general"

    def chat(self, prompt: str) -> tuple[str, str]:
        """Routes the prompt and returns (response, route_used)"""
        route = self.determine_route(prompt)
        logger.info(f"Hermes routed query to: {route}")
        
        try:
            # Query the integrated hybrid engine (combining SQL and RAG)
            response = self.rag.query_integrated(prompt)
        except Exception as e:
            logger.error(f"Integrated query failed: {e}")
            response = "Sorry, I encountered an error while processing your request."
            
        return response, route

