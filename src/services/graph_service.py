import os
import json
import logging
import re
import sqlite3
from src.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class GraphService:
    def __init__(self, rag_engine: RAGEngine):
        self.rag = rag_engine

    def get_knowledge_graph(self):
        """Extracts nodes and links from PageIndex 2.0 trees stored in the database."""
        nodes = []
        links = []
        seen_nodes = set()

        try:
            conn = sqlite3.connect(self.rag.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT doc_id, category, version, pre_op_physician_notes, 
                       procedure_physician_notes, post_op_short_physician_notes, 
                       maintenance_physician_notes 
                FROM page_index_trees
            """)
            rows = cursor.fetchall()
            conn.close()
        except Exception as db_e:
            logger.error(f"Failed to query page_index_trees for graph: {db_e}")
            rows = []

        for row in rows:
            doc_id = row['doc_id']
            if row['version'] != "2.0": continue
            
            # 1. Create a node for the document/topic
            filename = os.path.basename(doc_id)
            topic = filename
            for ext in ['.txt', '.pi.json', '.doc', '.docx', '.pdf', '.ppt', '.pptx']:
                topic = topic.replace(ext, '')
            topic = topic.strip()
            
            if topic not in seen_nodes:
                nodes.append({
                    "id": topic,
                    "type": "topic",
                    "category": row['category']
                })
                seen_nodes.add(topic)

            # 2. Check for Physician Notes as a high-value node type
            has_notes = (
                row['pre_op_physician_notes'] or 
                row['procedure_physician_notes'] or 
                row['post_op_short_physician_notes'] or 
                row['maintenance_physician_notes']
            )
            if has_notes:
                note_id = f"Note: {topic}"
                if note_id not in seen_nodes:
                    nodes.append({"id": note_id, "type": "physician_note"})
                    links.append({"source": topic, "target": note_id, "type": "has_correction"})
                    seen_nodes.add(note_id)

        # 3. Cross-document links (Optimized Semantic Overlap)
        topic_nodes = [n for n in nodes if n['type'] == 'topic']
        keyword_map = {} # {keyword: [node_ids]}
        
        # Pre-extract keywords for all nodes (O(N))
        for node in topic_nodes:
            node_id = node['id']
            # Find Chinese words of 2+ chars
            keywords = set(re.findall(r'[\u4e00-\u9fff]{2,}', node_id))
            for kw in keywords:
                if kw not in keyword_map: keyword_map[kw] = []
                keyword_map[kw].append(node_id)
        
        # Build links based on shared keywords (Faster than nested full regex)
        seen_links = set()
        for kw, linked_nodes in keyword_map.items():
            if len(linked_nodes) > 1:
                # Link all nodes sharing this keyword
                for i in range(len(linked_nodes)):
                    for j in range(i + 1, len(linked_nodes)):
                        u, v = sorted([linked_nodes[i], linked_nodes[j]])
                        link_key = f"{u}-{v}"
                        if link_key not in seen_links:
                            links.append({
                                "source": u,
                                "target": v,
                                "type": "related",
                                "keyword": kw
                            })
                            seen_links.add(link_key)
                        
                        # Limit density to prevent UI lag (max 5000 links)
                        if len(links) > 5000: break 
                    if len(links) > 5000: break
            if len(links) > 5000: break

        return {"nodes": nodes, "links": links}

graph_service = None # Initialized after RAGEngine

