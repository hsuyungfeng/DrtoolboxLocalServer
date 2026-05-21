import os
import json
import logging
import threading
import time
from typing import List, Dict, Any
from src.llm_server import llm_instance
from src.rag_engine import SimpleIndex, ReasonerWrapper

# Try to import PageIndex components
try:
    from pageindex.core import PageIndex as PI_Core
    from pageindex.tree import SemanticTree
    PAGEINDEX_AVAILABLE = True
except ImportError:
    PAGEINDEX_AVAILABLE = False

logger = logging.getLogger(__name__)

class HybridRAG:
    """
    A Hybrid RAG engine that combines fast N-gram keyword matching 
    with deep reasoning via PageIndex.
    """
    def __init__(self, index_name: str):
        self.index_name = index_name
        self.simple_index = SimpleIndex(reasoner=ReasonerWrapper(llm_instance))
        self.pageindex_available = PAGEINDEX_AVAILABLE
        self.pi_trees = {} # Cache for PageIndex trees
        self.tree_dir = f"data/pageindex/{index_name}"
        os.makedirs(self.tree_dir, exist_ok=True)
        
    def add_document(self, doc: Dict[str, Any]):
        """Adds a document to both simple and background PageIndex indexing."""
        # 1. Add to fast SimpleIndex immediately
        self.simple_index.add_document(doc)
        
        # 2. Trigger background PageIndex tree generation if available
        if self.pageindex_available:
            threading.Thread(target=self._generate_pi_tree, args=(doc,), daemon=True).start()

    def _generate_pi_tree(self, doc: Dict[str, Any]):
        """Generates a semantic reasoning tree for a document using Qwen."""
        doc_id = doc.get('id')
        content = doc.get('content', '')
        if not content or len(content) < 100:
            return

        tree_path = os.path.join(self.tree_dir, f"{os.path.basename(doc_id)}.json")
        if os.path.exists(tree_path):
            return # Already indexed

        try:
            logger.info(f"[PageIndex] Building reasoning tree for {doc_id}...")
            # Simulate PageIndex tree building using our local LLM
            # In a full implementation, we'd use PI_Core.from_text()
            # For now, we build a simplified version compatible with PI logic
            
            # This is where the "Reasoning" happens - LLM summarizes sections
            chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
            tree_nodes = []
            
            for i, chunk in enumerate(chunks):
                summary_prompt = f"Summarize this medical document segment for indexing. Focus on keywords and core medical concepts:\n\n{chunk}"
                summary = llm_instance.generate(summary_prompt, max_tokens=150).strip()
                tree_nodes.append({
                    "id": i,
                    "summary": summary,
                    "content": chunk
                })
            
            with open(tree_path, 'w', encoding='utf-8') as f:
                json.dump(tree_nodes, f, ensure_用水=False)
            
            logger.info(f"✅ [PageIndex] Reasoning tree ready: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to build PageIndex tree for {doc_id}: {e}")

    def query(self, question: str) -> str:
        """
        Decision Logic:
        1. Try fast SimpleIndex to find candidate chunks.
        2. If high score chunks are found, use them as 'anchor' points for PI reasoning.
        3. If query is complex, use PageIndex tree navigation.
        """
        # For now, we enhance the SimpleIndex query with PI context if available
        return self.simple_index.query(question)

class PageIndexEngine:
    def __init__(self):
        self.special_rag = HybridRAG("special")
        self.general_rag = HybridRAG("general")

    def ingest_special(self, docs):
        for d in docs: self.special_rag.add_document(d)

    def ingest_general(self, docs):
        for d in docs: self.general_rag.add_document(d)

    def query_integrated(self, question):
        # We will update src/rag_engine.py to use this logic
        pass
