# -*- coding: utf-8 -*-
"""
Graph-RAG Retrieval Engine
Queries structured medical knowledge from local SQLite.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GraphRAGEngine:
    def __init__(self, db_path: str = None):
        if db_path is None:
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(project_dir, 'data', 'db', 'clinic.db')
        else:
            self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def extract_nodes_by_matching(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract medical nodes from query using sliding window substring matches.
        Very fast and deterministic.
        """
        # Clean query
        clean_q = query.strip()
        if not clean_q:
            return []

        # Generate all substrings of length 2 to 10
        substrings = []
        q_len = len(clean_q)
        for length in range(2, min(11, q_len + 1)):
            for i in range(q_len - length + 1):
                substrings.append(clean_q[i:i+length])

        if not substrings:
            return []

        # Query database in single batch
        nodes = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # SQLite IN parameter placeholder
            placeholders = ",".join(["?"] * len(substrings))
            query_str = f"SELECT id, name, label FROM medical_nodes WHERE name IN ({placeholders})"
            cursor.execute(query_str, substrings)
            
            rows = cursor.fetchall()
            for r in rows:
                nodes.append({
                    "id": r[0],
                    "name": r[1],
                    "label": r[2]
                })
            conn.close()
        except Exception as e:
            logger.error(f"Failed to match nodes in SQLite: {e}")

        # Deduplicate and sort by length descending to prioritize longer matches (e.g. "肺氣腫" over "氣腫")
        nodes = sorted(nodes, key=lambda x: len(x["name"]), reverse=True)
        unique_nodes = []
        seen = set()
        for node in nodes:
            if node["name"] not in seen:
                seen.add(node["name"])
                unique_nodes.append(node)
                
        return unique_nodes

    def query_graph_context(self, query: str) -> str:
        """
        Extract nodes, fetch relationships, and format into context sentences.
        """
        matched_nodes = self.extract_nodes_by_matching(query)
        if not matched_nodes:
            return ""

        context_parts = []
        
        disease_ids = [n["id"] for n in matched_nodes if n["label"] == "Disease"]
        all_ids = [n["id"] for n in matched_nodes]

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 1. Fetch Disease Details
            if disease_ids:
                placeholders = ",".join(["?"] * len(disease_ids))
                cursor.execute(f"""
                    SELECT n.name, d.description, d.cause, d.prevent, d.cure_lasttime, d.cured_prob
                    FROM disease_details d
                    JOIN medical_nodes n ON d.node_id = n.id
                    WHERE n.id IN ({placeholders})
                """, disease_ids)
                
                for row in cursor.fetchall():
                    name, desc, cause, prevent, lasttime, prob = row
                    details = f"【{name}】\n"
                    if desc:
                        details += f"- 疾病描述：{desc}\n"
                    if cause:
                        details += f"- 疾病病因：{cause}\n"
                    if prevent:
                        details += f"- 預防措施：{prevent}\n"
                    if lasttime:
                        details += f"- 治療週期：{lasttime}\n"
                    if prob:
                        details += f"- 治癒機率：{prob}\n"
                    context_parts.append(details)

            # 2. Fetch Relationships / Edges
            if all_ids:
                placeholders = ",".join(["?"] * len(all_ids))
                cursor.execute(f"""
                    SELECT n1.name, n2.name, n2.label, e.relation
                    FROM medical_edges e
                    JOIN medical_nodes n1 ON e.source_id = n1.id
                    JOIN medical_nodes n2 ON e.target_id = n2.id
                    WHERE e.source_id IN ({placeholders})
                """, all_ids)
                
                relations = cursor.fetchall()
                
                # Group by source node and relation type to format output cleanly
                relation_map = {}
                for source, target, target_label, rel in relations:
                    key = (source, rel)
                    if key not in relation_map:
                        relation_map[key] = []
                    relation_map[key].append(target)
                
                relation_translations = {
                    "has_symptom": "伴隨症狀",
                    "acompany_with": "併發症",
                    "recommand_drug": "推薦藥品",
                    "common_drug": "常用藥品",
                    "need_check": "需要做的檢查",
                    "do_eat": "宜吃食物",
                    "no_eat": "忌吃食物",
                    "recommand_eat": "推薦食譜"
                }

                for (source, rel), targets in relation_map.items():
                    rel_name = relation_translations.get(rel, rel)
                    targets_str = "、".join(targets[:15])  # Cap at 15 items to save tokens
                    context_parts.append(f"根據醫學圖譜，【{source}】的{rel_name}包括：{targets_str}。")

            conn.close()
        except Exception as e:
            logger.error(f"Error querying graph database: {e}")

        return "\n".join(context_parts)
