import os
import json
import logging
import re
from src.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class GraphService:
    def __init__(self, rag_engine: RAGEngine):
        self.rag = rag_engine

    def get_knowledge_graph(self):
        """Extracts nodes and links from PageIndex 2.0 trees."""
        nodes = []
        links = []
        seen_nodes = set()

        with self.rag._pi_cache_lock:
            cache = list(self.rag._pi_cache)

        for item in cache:
            if item.get('version') != "2.0": continue
            
            # 1. Create a node for the document/topic
            doc_id = os.path.basename(item['id'])
            # Aggressive cleaning for medical filenames
            topic = doc_id
            for ext in ['.txt', '.pi.json', '.doc', '.docx', '.pdf', '.ppt', '.pptx']:
                topic = topic.replace(ext, '')
            topic = topic.strip()
            
            if topic not in seen_nodes:
                nodes.append({
                    "id": topic,
                    "type": "topic",
                    "category": "special" if "/special/" in item['id'] else "general"
                })
                seen_nodes.add(topic)

            # 2. Extract internal connections (Pre-op -> Procedure -> Post-op)
            # For now, we represent the logical flow within the document
            # Future enhancement: NLP extraction of cross-topic entities
            tree = item.get('tree', {})
            
            # Check for Physician Notes as a high-value node type
            if any("_physician_notes" in k for k in tree.keys()):
                note_id = f"Note: {topic}"
                if note_id not in seen_nodes:
                    nodes.append({"id": note_id, "type": "physician_note"})
                    links.append({"source": topic, "target": note_id, "type": "has_correction"})
                    seen_nodes.add(note_id)

        # 3. Cross-document links (Semantic Overlap)
        # Identify shared keywords between nodes
        topic_nodes = [n for n in nodes if n['type'] == 'topic']
        for i in range(len(topic_nodes)):
            for j in range(i + 1, len(topic_nodes)):
                t1 = topic_nodes[i]['id']
                t2 = topic_nodes[j]['id']
                
                # Check for word overlap (3+ chars)
                # This is a simple heuristic for logical connection
                words1 = set(re.findall(r'[\u4e00-\u9fff]{2,}', t1))
                words2 = set(re.findall(r'[\u4e00-\u9fff]{2,}', t2))
                overlap = words1.intersection(words2)
                
                if overlap:
                    links.append({
                        "source": t1,
                        "target": t2,
                        "type": "related",
                        "keywords": list(overlap)
                    })

        return {"nodes": nodes, "links": links}

graph_service = None # Initialized after RAGEngine
