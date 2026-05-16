# Note: Assuming pageindex provides a PageIndex class
# Adjust import based on the actual VectifyAI/PageIndex package structure
try:
    from pageindex import PageIndex
except ImportError:
    # Dummy mock for testing if pageindex isn't installed in the environment yet
    class PageIndex:
        def __init__(self, reasoner):
            self.reasoner = reasoner
        def add_document(self, doc):
            pass
        def query(self, q):
            return self.reasoner.reason(q)

from src.llm_server import llm_instance
import logging

logger = logging.getLogger(__name__)

class ReasonerWrapper:
    """Wrapper to make LocalLLM compatible with PageIndex reasoning interface."""
    def __init__(self, llm):
        self.llm = llm
        
    def reason(self, prompt):
        # Adapt to PageIndex's exact expected interface
        return self.llm.generate(prompt)

class RAGEngine:
    def __init__(self):
        self.reasoner = ReasonerWrapper(llm_instance)
        # Initialize two separate PageIndex trees for segregation
        self.special_index = PageIndex(reasoner=self.reasoner)
        self.general_index = PageIndex(reasoner=self.reasoner)
        
    def ingest_special_data(self, documents):
        logger.info(f"Ingesting {len(documents)} special documents into PageIndex.")
        for doc in documents:
            self.special_index.add_document(doc)
            
    def ingest_general_data(self, documents):
        logger.info(f"Ingesting {len(documents)} general documents into PageIndex.")
        for doc in documents:
            self.general_index.add_document(doc)
            
    def query(self, question, source="special"):
        """Route queries to the appropriate index."""
        logger.info(f"Querying {source} index: {question}")
        if source == "special":
            return self.special_index.query(question)
        else:
            return self.general_index.query(question)
