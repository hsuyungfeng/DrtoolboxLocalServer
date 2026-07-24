from src.llm_server import llm_instance
import logging
import json
import sqlite3
import os
import datetime
import re
import threading
import concurrent.futures
from config.settings import DATA_DIR, PROJECT_ROOT
from src.rag.graph_rag_engine import GraphRAGEngine

logger = logging.getLogger(__name__)

# Global database lock to prevent concurrent write issues in SQLite
db_write_lock = threading.Lock()

class ReasonerWrapper:
    """Wrapper to make LocalLLM compatible with reasoning interface."""
    def __init__(self, llm):
        self.llm = llm
        
    def reason(self, prompt):
        return self.llm.generate(prompt)

    def reason_chat(self, messages):
        return self.llm.chat_generate(messages)

    def reason_chat_stream(self, messages):
        return self.llm.chat_generate_stream(messages)

class SimpleIndex:
    def __init__(self, reasoner, category, db_path):
        self.reasoner = reasoner
        self.category = category
        self.db_path = db_path
        self.lock = threading.Lock()
        
    def add_document(self, doc):
        doc_id = doc.get('id', '')
        content = doc.get('content', '')
        if not content:
            return
            
        # Write chunks directly to SQLite database
        with db_write_lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                # Delete existing chunks for this document and category to prevent duplicates
                cursor.execute("DELETE FROM rag_chunks WHERE doc_id = ? AND category = ?", (doc_id, self.category))
                
                # Chunk document and insert
                chunk_index = 0
                for i in range(0, len(content), 400):
                    chunk_text = content[i:i+600]
                    cursor.execute("""
                        INSERT INTO rag_chunks (doc_id, category, chunk_index, content)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, self.category, chunk_index, chunk_text))
                    chunk_index += 1
                    
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to add document chunks to SQLite: {e}")
        
    def get_scored_chunks(self, q):
        # Format query for FTS5 Match
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', q)
        stop_words = {
            "請問", "在哪", "哪裡", "多少", "類似", "療程", "治療", "多久", "可以", 
            "注意", "什麼", "如果", "出現", "情況", "需要", "立即", "如何", "是不是", 
            "有沒有", "現在", "一個", "一些", "以及", "關於", "建議", "提供", "就醫",
            "回診", "或者", "還是"
        }
        filtered_kvs = [k for k in keywords if k not in stop_words and not any(sw in k for sw in ["請問", "什麼", "可以", "需要", "有沒有"])]
        if not filtered_kvs:
            filtered_kvs = keywords if keywords else list(q.replace("?", "").replace("？", "").replace(" ", "").replace("請問", ""))
            
        if not filtered_kvs:
            return []
            
        fts_query = " OR ".join([f'"{k}"' for k in filtered_kvs])
        scored_chunks = []
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Query candidate chunks using FTS5 (sub-millisecond retrieval)
            cursor.execute("""
                SELECT c.content, bm25(rag_chunks_fts) as score FROM rag_chunks c
                JOIN rag_chunks_fts f ON c.id = f.rowid
                WHERE c.category = ? AND rag_chunks_fts MATCH ?
                ORDER BY score ASC
                LIMIT 30
            """, (self.category, fts_query))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Compute fine-grained N-gram overlap scores on the top 30 candidates
            clean_q = q.replace("?", "").replace("？", "").replace(" ", "").replace("請問", "")
            q_chars = set(clean_q)
            ngrams = []
            for n in range(2, 6):
                if n <= len(clean_q):
                    for i in range(len(clean_q) - n + 1):
                        ngrams.append(clean_q[i:i+n])
            
            for content, bm25_score in rows:
                score = 0
                score += sum(1.5 for char in q_chars if char in content)
                for ngram in ngrams:
                    count = content.count(ngram)
                    if count > 0:
                        score += count * (len(ngram) ** 2.5) * 15
                if score > 5:
                    scored_chunks.append((score, content))
                    
        except Exception as e:
            logger.error(f"SQL get_scored_chunks failed for category {self.category}: {e}")
            
        return scored_chunks

class RAGEngine:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, 'db', 'rag.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self.graph_engine = GraphRAGEngine()
        
        self.reasoner = ReasonerWrapper(llm_instance)
        self.special_index = SimpleIndex(reasoner=self.reasoner, category="special", db_path=self.db_path)
        self.general_index = SimpleIndex(reasoner=self.reasoner, category="general", db_path=self.db_path)
        
        # Parallel page indexing pool
        self.pi_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="PI_Worker")
        
    def _init_db(self):
        """Initializes database schema and FTS5 search engines for chunks and reasoning trees."""
        with db_write_lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # 1. RAG chunks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rag_chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id TEXT,
                        category TEXT,
                        chunk_index INTEGER,
                        content TEXT
                    )
                """)
                
                # 2. RAG chunks FTS5 virtual table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_chunks_fts'")
                if not cursor.fetchone():
                    cursor.execute("""
                        CREATE VIRTUAL TABLE rag_chunks_fts USING fts5(
                            content,
                            content='rag_chunks',
                            content_rowid='id',
                            tokenize='unicode61'
                        )
                    """)
                    cursor.execute("""
                        CREATE TRIGGER IF NOT EXISTS rag_chunks_ai AFTER INSERT ON rag_chunks BEGIN
                            INSERT INTO rag_chunks_fts(rowid, content) VALUES (new.id, new.content);
                        END
                    """)
                    cursor.execute("""
                        CREATE TRIGGER IF NOT EXISTS rag_chunks_ad AFTER DELETE ON rag_chunks BEGIN
                            INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
                        END
                    """)
                    cursor.execute("""
                        CREATE TRIGGER IF NOT EXISTS rag_chunks_au AFTER UPDATE ON rag_chunks BEGIN
                            INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
                            INSERT INTO rag_chunks_fts(rowid, content) VALUES (new.id, new.content);
                        END
                    """)
                    
                # 3. PageIndex trees table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS page_index_trees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id TEXT UNIQUE,
                        category TEXT,
                        pre_op TEXT,
                        pre_op_physician_notes TEXT,
                        procedure TEXT,
                        procedure_physician_notes TEXT,
                        post_op_short TEXT,
                        post_op_short_physician_notes TEXT,
                        maintenance TEXT,
                        maintenance_physician_notes TEXT,
                        summary_text TEXT,
                        version TEXT,
                        indexed_at TEXT
                    )
                """)
                
                # 4. PageIndex FTS5 virtual table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='page_index_fts'")
                if not cursor.fetchone():
                    cursor.execute("""
                        CREATE VIRTUAL TABLE page_index_fts USING fts5(
                            summary_text,
                            content='page_index_trees',
                            content_rowid='id',
                            tokenize='unicode61'
                        )
                    """)
                    cursor.execute("""
                        CREATE TRIGGER IF NOT EXISTS page_index_ai AFTER INSERT ON page_index_trees BEGIN
                            INSERT INTO page_index_fts(rowid, summary_text) VALUES (new.id, new.summary_text);
                        END
                    """)
                    cursor.execute("""
                        CREATE TRIGGER IF NOT EXISTS page_index_ad AFTER DELETE ON page_index_trees BEGIN
                            INSERT INTO page_index_fts(page_index_fts, rowid, summary_text) VALUES('delete', old.id, old.summary_text);
                        END
                    """)
                    cursor.execute("""
                        CREATE TRIGGER IF NOT EXISTS page_index_au AFTER UPDATE ON page_index_trees BEGIN
                            INSERT INTO page_index_fts(page_index_fts, rowid, summary_text) VALUES('delete', old.id, old.summary_text);
                            INSERT INTO page_index_fts(rowid, summary_text) VALUES (new.id, new.summary_text);
                        END
                    """)
                    
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to initialize SQLite RAG database: {e}")
                
    def ingest_special_data(self, documents):
        logger.info(f"Ingesting {len(documents)} special documents into Index.")
        for doc in documents:
            if not doc.get('content'): continue
            self.special_index.add_document(doc)
            self.pi_executor.submit(self._background_pi_index, doc, "special")
            
    def ingest_general_data(self, documents):
        logger.info(f"Ingesting {len(documents)} general documents into Index.")
        for doc in documents:
            if not doc.get('content'): continue
            self.general_index.add_document(doc)
            self.pi_executor.submit(self._background_pi_index, doc, "general")

    def _background_pi_index(self, doc, category):
        """Worker task for building semantic reasoning trees."""
        doc_id = doc.get('id', '')
        content = doc.get('content', '')
        if not content or len(content) < 300: return
        
        # Check if reasoning tree already exists in database
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("SELECT doc_id FROM page_index_trees WHERE doc_id = ?", (doc_id,))
            exists = cursor.fetchone()
            conn.close()
            if exists:
                return # Already built
        except Exception as e:
            logger.error(f"Failed checking tree existence: {e}")
            
        try:
            tree_system = "你是一個醫療文件分析專家。請將輸入的文件內容轉化為結構化的 JSON 推理樹。請勿輸出 JSON 以外的任何文字（除思考過程外）。"
            tree_prompt = f"""請分析以下醫療/診所文件，並生成一個「結構化推理樹」。
要求：
1. 必須嚴格遵守以下 JSON 格式。
2. 內容必須為專業繁體中文。
3. 如果某個部分在文件中沒提到，請填入「無相關資料」。

格式如下：
{{
    "pre_op": "術前須知與禁忌（包含對象、過敏、禁食等）",
    "procedure": "療程步驟與原理（包含麻醉方式、時間、運作原理）",
    "post_op_short": "術後立即照護 (1-7天)（包含冰敷、洗臉、用藥）",
    "maintenance": "長期維持與保養（包含防曬、回診頻率、併發症監控）"
}}

文件內容：
{content[:6000]}
"""
            messages = [
                {"role": "system", "content": tree_system},
                {"role": "user", "content": tree_prompt}
            ]
            
            tree_raw = self.reasoner.reason_chat(messages).strip()
            if "<think>" in tree_raw: tree_raw = tree_raw.split("</think>")[-1].strip()
            
            # Extract JSON block
            import re
            json_match = re.search(r'\{.*\}', tree_raw, re.DOTALL)
            if json_match:
                tree_data = json.loads(json_match.group())
            else:
                # Fallback to a single summary if JSON fails
                tree_data = {
                    "pre_op": "解析失敗",
                    "procedure": tree_raw[:500],
                    "post_op_short": "解析失敗",
                    "maintenance": "解析失敗"
                }
            
            summary_text = f"{tree_data.get('pre_op')} {tree_data.get('procedure')} {tree_data.get('post_op_short')} {tree_data.get('maintenance')}"
            
            # Persistent database write
            with db_write_lock:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                # Delete existing to trigger FTS update correctly
                cursor.execute("DELETE FROM page_index_trees WHERE doc_id = ?", (doc_id,))
                
                cursor.execute("""
                    INSERT INTO page_index_trees 
                    (doc_id, category, pre_op, pre_op_physician_notes, procedure, procedure_physician_notes,
                     post_op_short, post_op_short_physician_notes, maintenance, maintenance_physician_notes,
                     summary_text, version, indexed_at)
                    VALUES (?, ?, ?, NULL, ?, NULL, ?, NULL, ?, NULL, ?, ?, ?)
                """, (doc_id, category, tree_data.get('pre_op'), tree_data.get('procedure'),
                      tree_data.get('post_op_short'), tree_data.get('maintenance'),
                      summary_text, "2.0", str(datetime.datetime.now())))
                      
                conn.commit()
                conn.close()
            logger.info(f"✅ [PageIndex] Clinical Reasoning Tree ready in database: {os.path.basename(doc_id)}")
        except Exception as e:
            logger.error(f"PageIndex build failed for {doc_id}: {e}")

    def query(self, question, route="special", image_data=None):
        return self.query_integrated(question, route=route, image_data=image_data)

    def inject_verified_knowledge(self, question, answer, metadata):
        """Dynamic Knowledge Backflow: Injects physician corrections into PageIndex trees."""
        logger.info(f"🔄 Injecting knowledge backflow for: {question[:30]}...")
        
        # 1. Identify which tree node this belongs to
        target_node = "procedure" # default
        if any(k in question for k in ["術前", "禁忌", "過敏", "準備"]): target_node = "pre_op"
        elif any(k in question for k in ["術後", "洗臉", "冰敷", "化妝", "修養"]): target_node = "post_op_short"
        elif any(k in question for k in ["維持", "多久", "保養", "防曬", "效果"]): target_node = "maintenance"

        # 2. Find the most relevant existing tree in database
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', question)
        fts_query = " OR ".join([f'"{k}"' for k in keywords if k not in ["請問", "療程"]])
        
        best_doc_id = None
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()
        
        if fts_query:
            try:
                cursor.execute("""
                    SELECT t.doc_id FROM page_index_trees t
                    JOIN page_index_fts f ON t.id = f.rowid
                    WHERE page_index_fts MATCH ?
                    LIMIT 1
                """, (fts_query,))
                row = cursor.fetchone()
                if row:
                    best_doc_id = row[0]
            except Exception as e:
                logger.error(f"FTS lookup for backflow failed: {e}")
                
        # If no FTS match, find using basic substring match in doc_id
        if not best_doc_id:
            try:
                cursor.execute("SELECT doc_id FROM page_index_trees")
                all_docs = [r[0] for r in cursor.fetchall()]
                best_score = 0
                for doc_id in all_docs:
                    score = sum(50 for k in keywords if k in os.path.basename(doc_id))
                    if score > best_score:
                        best_score = score
                        best_doc_id = doc_id
            except Exception as e:
                logger.error(f"Fallback lookup for backflow failed: {e}")

        if best_doc_id:
            logger.info(f"📍 Matching database entry found: {os.path.basename(best_doc_id)}")
            try:
                note_key = f"{target_node}_physician_notes"
                cursor.execute(f"SELECT {note_key}, pre_op, procedure, post_op_short, maintenance, pre_op_physician_notes, procedure_physician_notes, post_op_short_physician_notes, maintenance_physician_notes FROM page_index_trees WHERE doc_id = ?", (best_doc_id,))
                row = cursor.fetchone()
                if row:
                    existing_notes = row[0] or ""
                    pre_op, procedure, post_op_short, maintenance = row[1], row[2], row[3], row[4]
                    pre_notes, proc_notes, post_notes, maint_notes = row[5] or "", row[6] or "", row[7] or "", row[8] or ""
                    
                    new_note = f"【醫師校正】: {answer}"
                    if new_note not in existing_notes:
                        updated_notes = f"{existing_notes}\n{new_note}".strip()
                        
                        # Apply local note change
                        local_notes = {
                            "pre_op_physician_notes": pre_notes,
                            "procedure_physician_notes": proc_notes,
                            "post_op_short_physician_notes": post_notes,
                            "maintenance_physician_notes": maint_notes
                        }
                        local_notes[note_key] = updated_notes
                        
                        # Update notes & summary
                        summary_text = f"{pre_op} {procedure} {post_op_short} {maintenance} {local_notes['pre_op_physician_notes']} {local_notes['procedure_physician_notes']} {local_notes['post_op_short_physician_notes']} {local_notes['maintenance_physician_notes']}"
                        
                        with db_write_lock:
                            cursor.execute(f"""
                                UPDATE page_index_trees 
                                SET {note_key} = ?, summary_text = ?, indexed_at = ?
                                WHERE doc_id = ?
                            """, (updated_notes, summary_text, str(datetime.datetime.now()), best_doc_id))
                            conn.commit()
                        logger.info(f"💾 PageIndex DB record for '{best_doc_id}' updated atomically.")
            except Exception as e:
                logger.error(f"Failed to update PageIndex record: {e}")
        else:
            logger.warning("⚠️ No matching PageIndex entry found for backflow.")
            
        conn.close()

    def _get_context(self, question, route="special"):
        """Internal helper to gather SQL, PI, and RAG context with Physician Note priority."""
        logger.info(f"[_get_context] Starting context gathering for route '{route}'...")
        db_path = os.path.join(DATA_DIR, 'db', 'clinic.db')
        sql_context = "無相關資料庫紀錄。"
        
        # 1. SQL Operational Data Lookup
        if route == "special" and os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Fetch basic clinic details for all special route queries
                cursor.execute("SELECT clinic_name_chinese, phone, address, website FROM clinic_info LIMIT 1")
                clinic_row = cursor.fetchone()
                if clinic_row:
                    sql_context = f"診所基本資訊: {clinic_row[0]}, 電話: {clinic_row[1]}, 地址: {clinic_row[2]}, 網站: {clinic_row[3]}"
                
                if any(k in question for k in ["門診", "時間", "開", "休息", "排班"]):
                    cursor.execute("SELECT day_of_week, morning_start, morning_end, afternoon_start, afternoon_end, evening_start, evening_end FROM v_clinic_hours_this_week LIMIT 7")
                    records = cursor.fetchall()
                    if records: sql_context += f"\n診所門診時間表:\n{records}"
                
                # Dynamic OTC Drug Localization Mapping
                if any(k in question for k in ["藥", "普拿疼", "退燒", "止痛", "感冒", "抗生素", "成分", "用藥", "副作用", "布洛芬"]):
                    try:
                        cursor.execute("SELECT ingredient, otc_name FROM drugs WHERE otc_name IS NOT NULL GROUP BY ingredient LIMIT 30")
                        otc_mappings = cursor.fetchall()
                        if otc_mappings:
                            mapping_str = ", ".join([f"{row[0]} -> {row[1]}" for row in otc_mappings])
                            sql_context += f"\n本診所藥物成分本地化對照表 (OTC Mapping): {mapping_str}"
                    except Exception as e:
                        logger.warning(f"Failed to fetch OTC mappings: {e}")
                        
                conn.close()
            except Exception as e: logger.error(f"SQL Error: {e}")
        logger.info(f"[_get_context] SQL done. sql_context length: {len(sql_context)}")

        # 2. PageIndex (Semantic Memory)
        logger.info(f"[_get_context] Querying PageIndex for route '{route}'...")
        pi_context_list = []
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', question) 
        
        # Filter common Chinese stop words to avoid matching generic query helpers
        stop_words = {
            "請問", "在哪", "哪裡", "多少", "類似", "療程", "治療", "多久", "可以", 
            "注意", "什麼", "如果", "出現", "情況", "需要", "立即", "如何", "是不是", 
            "有沒有", "現在", "一個", "一些", "以及", "關於", "建議", "提供", "就醫",
            "回診", "或者", "還是"
        }
        filtered_keywords = [k for k in keywords if k not in stop_words and not any(sw in k for sw in ["請問", "什麼", "可以", "需要", "有沒有"])]
        if not filtered_keywords:
            filtered_keywords = keywords
            
        if filtered_keywords:
            fts_query = " OR ".join([f'"{k}"' for k in filtered_keywords])
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                # Fetch matching PageIndex trees from database FTS index
                cursor.execute("""
                    SELECT t.doc_id, t.pre_op, t.procedure, t.post_op_short, t.maintenance,
                           t.pre_op_physician_notes, t.procedure_physician_notes, 
                           t.post_op_short_physician_notes, t.maintenance_physician_notes
                    FROM page_index_trees t
                    JOIN page_index_fts f ON t.id = f.rowid
                    WHERE t.category = ? AND page_index_fts MATCH ?
                    LIMIT 10
                """, (route, fts_query))
                
                rows = cursor.fetchall()
                conn.close()
                
                for row in rows:
                    doc_id, pre_op, procedure, post_op_short, maintenance, \
                    pre_notes, proc_notes, post_notes, maint_notes = row
                    
                    doc_filename = os.path.basename(doc_id)
                    relevant_parts = []
                    
                    # 1. Match category keywords
                    if any(k in question for k in ["術前", "禁忌", "過敏", "注意"]):
                        if pre_notes: relevant_parts.append(f"🌟 [醫師權威指令]: {pre_notes}")
                        if pre_op and pre_op not in ["無相關資料", "解析失敗"]:
                            relevant_parts.append(f"[術前須知]: {pre_op}")
                    
                    if any(k in question for k in ["步驟", "原理", "怎麼做", "多長"]):
                        if proc_notes: relevant_parts.append(f"🌟 [醫師權威指令]: {proc_notes}")
                        if procedure and procedure not in ["無相關資料", "解析失敗"]:
                            relevant_parts.append(f"[療程原理]: {procedure}")
                    
                    if any(k in question for k in ["術後", "洗臉", "冰敷", "化妝", "運動"]):
                        if post_notes: relevant_parts.append(f"🌟 [醫師權威指令]: {post_notes}")
                        if post_op_short and post_op_short not in ["無相關資料", "解析失敗"]:
                            relevant_parts.append(f"[立即照護]: {post_op_short}")
                    
                    if any(k in question for k in ["維持", "多久打一次", "效果", "防曬"]):
                        if maint_notes: relevant_parts.append(f"🌟 [醫師權威指令]: {maint_notes}")
                        if maintenance and maintenance not in ["無相關資料", "解析失敗"]:
                            relevant_parts.append(f"[長期保養]: {maintenance}")
                    
                    # Fallback 1: match keywords inside sections
                    if not relevant_parts:
                        for name, val, note in [
                            ("術前須知", pre_op, pre_notes),
                            ("療程原理", procedure, proc_notes),
                            ("立即照護", post_op_short, post_notes),
                            ("長期保養", maintenance, maint_notes)
                        ]:
                            if val and val not in ["無相關資料", "解析失敗"] and any(k in val for k in filtered_keywords):
                                if note: relevant_parts.append(f"🌟 [醫師權威指令]: {note}")
                                relevant_parts.append(f"[{name}]: {val}")
                                
                    # Fallback 2: if still empty and title matches, add all valid sections
                    title_match = any(k in doc_filename for k in filtered_keywords)
                    if not relevant_parts and title_match:
                        for name, val, note in [
                            ("術前須知", pre_op, pre_notes),
                            ("療程原理", procedure, proc_notes),
                            ("立即照護", post_op_short, post_notes),
                            ("長期保養", maintenance, maint_notes)
                        ]:
                            if val and val not in ["無相關資料", "解析失敗"]:
                                if note: relevant_parts.append(f"🌟 [醫師權威指令]: {note}")
                                relevant_parts.append(f"[{name}]: {val}")
                                
                    summary_text = "\n".join(relevant_parts)
                    
                    # Compute score to rank candidates
                    title_score = sum(50 for k in filtered_keywords if k in doc_filename)
                    content_score = sum(10 for k in filtered_keywords if k in summary_text)
                    score = title_score + content_score
                    
                    if score > 0 and summary_text.strip():
                        pi_context_list.append((score, f"【文件: {doc_filename}】\n{summary_text}"))
            except Exception as e:
                logger.error(f"SQL PageIndex context query failed: {e}")
                
        logger.info(f"[_get_context] PageIndex done. Found {len(pi_context_list)} candidate matches for route '{route}'.")
        pi_context_list.sort(reverse=True, key=lambda x: x[0])
        pi_context = "\n\n".join([x[1] for x in pi_context_list[:3]])
        if not pi_context: pi_context = "無相關深度推理摘要。"
        logger.info(f"[_get_context] PageIndex top 3 selected. Context length: {len(pi_context)}")

        # 3. SimpleIndex Context Lookup
        logger.info(f"[_get_context] Querying SimpleIndex (route: {route})...")
        if route == "special":
            rag_scored_chunks = self.special_index.get_scored_chunks(question)
        else:
            rag_scored_chunks = self.general_index.get_scored_chunks(question)
            
        rag_scored_chunks.sort(reverse=True, key=lambda x: x[0])
        top_chunks = []
        seen = set()
        for score, chunk in rag_scored_chunks:
            if chunk not in seen:
                seen.add(chunk)
                text = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電確認]', chunk)
                text = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電確認]', text)
                top_chunks.append(text)
            if len(top_chunks) >= 4: break 
        rag_context = "\n\n".join(top_chunks)
        if not rag_context: rag_context = "無相關原始文本片段。"
        logger.info(f"[_get_context] SimpleIndex done. Context length: {len(rag_context)}")
        
        return sql_context, pi_context, rag_context

    def query_integrated(self, question, route="special", image_data=None, force_llm_knowledge=False):
        logger.info(f"Deep Hybrid Reasoning ({route}) for: {question} (image: {image_data is not None}, force_llm: {force_llm_knowledge})")
        sql_context, pi_context, rag_context = self._get_context(question, route=route)
        
        # 1. First, get the answer
        # ----------------------------------------------------
        # 2.5. 查詢醫療知識圖譜 (Graph-RAG 關聯資料)
        # ----------------------------------------------------
        graph_raw = self.graph_engine.query_graph_context(question)
        if graph_raw:
            graph_context = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電診所確認]', graph_raw)
            graph_context = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電診所確認]', graph_context)
            graph_context = re.sub(r'(?:價格|售價|特價|優惠價|費用|價值)[\s:：]*\d+(?:,\d+)*', '價格[請致電診所確認]', graph_context)
            graph_context = re.sub(r'\d+\s*[堂次管]\s*/\s*[$]?\s*\d+(?:,\d+)*', '[請致電診所確認]', graph_context)
            graph_context = re.sub(r'(?<!\d)(?!(?:202\d|11\d)\b)[1-9]\d{3,7}(?!\d)', '[請致電診所確認]', graph_context)
            graph_context = re.sub(r'(?<!\d)[1-9]\d{0,2}(?:,\d{3})+(?!\d)', '[請致電診所確認]', graph_context)
            graph_context = re.sub(r'(?:CC|U|瓶|堂|次)[\s/]+\d+(?:,\d+)*', ' [請致電診所確認]', graph_context, flags=re.IGNORECASE)
        else:
            graph_context = "無相關醫學知識圖譜資料。"
        current_date = datetime.date.today()
        if image_data:
            user_content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        else:
            user_content = question

        if route == "special":
            # Simulation/Drafting mode fallback logic
            if force_llm_knowledge:
                not_found_instruction = "4. **找不到資料時**：若內部資料庫中沒有相關資訊，請根據你的「專業醫療與醫美知識」提供一個初步草案回答，並在回答開頭標註『[AI 預擬草案]』，供醫師後續校正。"
            else:
                not_found_instruction = "4. **找不到資料時**：若真的完全沒有關於該主題的資料，請禮貌告知：「目前無法確認該活動的時效與具體內容，為避免提供錯誤資訊，建議您致電診所向專人諮詢以獲取最準確的報價喔！」"

            system_instruction = f"""你是一個具備頂尖『PageIndex 深度推理』能力的專業醫美與診所 AI 助理。今天是 {current_date}。
你的任務是從提供的資料中「挖掘」出最精確長度之醫學與術後建議。
{'如果你看到圖片，請結合圖片中的臨床徵兆進行分析。' if image_data else ''}

【核心資料來源：PageIndex 專業摘要 (具備高層次邏輯)】
{pi_context}

【輔助資料來源：原始文本片段 (具備細節)】
{rag_context}

【基礎資料來源：診所資料庫 (營運相關)】
{sql_context}

【關聯資料來源：醫學知識圖譜 (關聯推導結果)】
{graph_context}

【專業回答指南】
1. **嚴禁簡體中文**：全程必須使用繁體中文。
2. **優先權**：若 PageIndex 摘要中有提到具體醫學流程或術後原則，請優先採用。
3. **禁止報價**：絕對不能出現任何金錢數字、價格資訊。遇到價格一律引導致電診所。
4. **藥名本地化**：提及「乙醯胺酚」時，請寫為「俗稱普拿疼的乙醯胺酚」；提及「布洛芬」時，請寫為「常見的布洛芬」。
5. **預約與互動引導**：如果查詢與「頭痛」或臨床症狀相關，請務必在結尾加入以下內容：
   - 警示引導：「若您有上述紅旗症狀，或是頭痛已影響日常，建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。」
   - 互動提問：「若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！」
{not_found_instruction}"""
        else:
            # General Knowledge Mode
            system_instruction = f"""你是一個專業的醫學與健康知識 AI 助理。今天是 {current_date}。
你可以結合「提供的參考資料」與你的「專業醫學知識庫」來回答使用者的健康問題。
{'如果你看到圖片，請結合圖片中的徵兆進行分析。' if image_data else ''}

【參考資料 (診所提供)】
{pi_context}
{rag_context}

【關聯參考資料 (知識圖譜)】
{graph_context}

【回答原則】
1. **結合知識**：如果參考資料中沒有提到，請使用你的專業醫學知識進行回答，確保資訊正確且有益。
2. **專業且繁體**：使用親切且專業的繁體中文回答.
3. **安全性**：提醒使用者你的建議僅供參考，若症狀持續應尋求醫師診斷。
4. **嚴禁報價**：絕對禁止提及 any 具體價格。
5. **藥名本地化**：提及「乙醯胺酚」時，請一律寫為「俗稱普拿疼的乙醯胺酚」；提及「布洛芬」時，請一律寫為「常見的布洛芬」。
6. **預約與互動引導**：如果查詢與「頭痛」或臨床症狀相關，請在回答末尾加入以下內容：
   - 警示引導：「若您有上述紅旗症狀，或是頭痛已影響日常，建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。」
   - 互動提問：「若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！」"""

        messages = [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        answer = self.reasoner.reason_chat(messages).strip()

        # Post-process answer for localized OTC drugs & reservation CTA/engagement (robust fallback)
        if "乙醯胺酚" in answer and "俗稱普拿疼" not in answer:
            answer = answer.replace("乙醯胺酚", "俗稱普拿疼的乙醯胺酚")
        if "布洛芬" in answer and "常見的" not in answer:
            answer = answer.replace("布洛芬", "常見的布洛芬")

        is_headache_query = any(k in question for k in ["頭痛", "偏頭痛", "腦袋痛", "頭暈痛"])
        if is_headache_query:
            if "預約門診" not in answer:
                answer += "\n\n建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。"
            if "若您能補充頭痛的部位" not in answer:
                answer += "\n\n若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！"

        # 2. Ask LLM to evaluate its own confidence
        eval_prompt = f"""請針對你剛才的回答（問題：『{question}』）進行評分。

評分邏輯：
- 100分：如果是診所資訊，答案完全對應資料來源；如果是醫療常識，答案準確且專業。
- 80分：答案核心正確，但部分細節來自通用知識補充。
- 50分：資料來源模糊，你主要靠推論回答。
- 10分：完全沒有資料，你也無法確定答案。

請僅回傳一個數字（如 95 或 40），不要有任何其他文字說明。"""
        
        try:
            score_res = llm_instance.generate(eval_prompt, max_tokens=10).strip()
            if "<think>" in score_res: score_res = score_res.split("</think>")[-1].strip()
            digits = re.findall(r'\d+', score_res)
            confidence_score = int(digits[0]) if digits else 50
        except Exception as e:
            logger.error(f"Scoring error: {e}")
            confidence_score = 50 
            
        return answer, confidence_score

    def query_integrated_stream(self, question, route="special", image_data=None, force_llm_knowledge=False):
        logger.info(f"Deep Hybrid Reasoning (Stream, {route}) for: {question} (image: {image_data is not None}, force_llm: {force_llm_knowledge})")
        sql_context, pi_context, rag_context = self._get_context(question, route=route)
        
        current_date = datetime.date.today()
        
        # Multimodal Content
        if image_data:
            user_content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        else:
            user_content = question

        if route == "special":
            if force_llm_knowledge:
                not_found_instruction = "4. **找不到資料時**：若內部資料庫中沒有相關資訊，請根據你的「專業醫療與醫美知識」提供一個初步草案回答，並在回答開頭標註『[AI 預擬草案]』，供醫師後續校正。"
            else:
                not_found_instruction = "4. **找不到資料時**：若真的完全沒有關於該主題的資料，請告知：「目前無法確認該活動的時效與具體內容，為避免提供錯誤資訊，建議您致電診所向專人諮詢以獲取最準確的報價喔！」"

            system_instruction = f"""你是一個具備頂尖『PageIndex 深度推理』能力的專業醫美與診所 AI 助理。今天是 {current_date}。
        你的任務是從提供的資料中「挖掘」出最精確長度之醫學與術後建議。
        {'如果你看到圖片，請結合圖片中的臨床徵兆進行分析。' if image_data else ''}

        【核心資料來源：PageIndex 專業摘要 (具備高層次邏輯)】
        {pi_context}

        【輔助資料來源：原始文本片段 (具備細節)】
        {rag_context}

        【基礎資料來源：診所資料庫 (營運相關)】
        {sql_context}

        【專業回答指南】
        1. **嚴禁簡體中文**：全程必須使用繁體中文。
        2. **優先權**：若 PageIndex 摘要中有提到具體醫學流程或術後原則，請優先採用。
        3. **禁止報價**：絕對不能出現任何金錢數字、價格資訊。遇到價格一律引導致電診所。
        4. **藥物名稱在地化 (OTC Localization)**：提及任何藥物成分時，務必對照並使用【本診所藥物成分本地化對照表】中的中文俗名（例如：若成分為 ACETAMINOPHEN，請一律回答「普拿疼 (退燒止痛藥)」），讓病患容易理解。
        5. **預約與互動引導**：如果查詢與「頭痛」或臨床症狀相關，請務必在結尾加入以下內容：
           - 警示引導：「若您有上述紅旗症狀，或是頭痛已影響日常，建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。」
           - 互動提問：「若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！」
        {not_found_instruction}"""

        else:
            system_instruction = f"""你是一個專業的醫學與健康知識 AI 助理。今天是 {current_date}。
        你可以結合「提供的參考資料」與你的「專業醫學知識庫」來回答使用者的健康問題。
        {'如果你看到圖片，請結合圖片中的徵兆進行分析。' if image_data else ''}

        【參考資料 (診所提供)】
        {pi_context}
        {rag_context}

        【回答原則】
        1. **結合知識**：如果參考資料中沒有提到，請使用你的專業醫學知識進行回答。
        2. **專業且繁體**：使用親切且專業的繁體中文回答。
        3. **安全性**：提醒使用者你的建議僅供參考。
        4. **嚴禁報價**：絕對禁止任價格。
        5. **藥物名稱在地化 (OTC Localization)**：提及任何藥物成分時，務必對照並使用【本診所藥物成分本地化對照表】中的中文俗名（例如：若成分為 ACETAMINOPHEN，請一律回答「普拿疼 (退燒止痛藥)」），讓病患容易理解。
        6. **預約與互動引導**：如果查詢與「頭痛」或臨床症狀相關，請在回答末尾加入以下內容：
           - 警示引導：「若您有上述紅旗症狀，或是頭痛已影響日常，建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。」
           - 互動提問：「若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！」"""

        messages = [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        full_answer = ""
        for chunk in self.reasoner.reason_chat_stream(messages):
            if chunk:
                full_answer += chunk
                yield chunk

        # Evaluate confidence after stream finishes
        eval_prompt = f"""針對剛才的回答（內容摘要：{full_answer[:200]}...），請評估其準確度與專業程度。
如果是診所資訊，請評估其與資料來源的符合度；如果是醫療常識，請評估其是否準確專業。
請給出 1 到 100 的分數。只需回傳純數字。"""
        try:
            score_res = llm_instance.generate(eval_prompt, max_tokens=10).strip()
            if "<think>" in score_res: score_res = score_res.split("</think>")[-1].strip()
            confidence_score = int(re.search(r'\d+', score_res).group())
        except:
            confidence_score = 50
            
        yield f"__CONFIDENCE_SCORE__{confidence_score}"
