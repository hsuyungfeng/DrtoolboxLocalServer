from src.llm_server import llm_instance
import logging
import json
import sqlite3
import os
import datetime
import re
from config.settings import DATA_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

class ReasonerWrapper:
    """Wrapper to make LocalLLM compatible with reasoning interface."""
    def __init__(self, llm):
        self.llm = llm
        
    def reason(self, prompt):
        return self.llm.generate(prompt)

    def reason_chat(self, messages):
        return self.llm.chat_generate(messages)

class SimpleIndex:
    def __init__(self, reasoner):
        self.reasoner = reasoner
        self.documents = []
        self.chunks = [] # Cache for faster search
        
    def add_document(self, doc):
        # 如果上傳同名檔案，直接覆蓋舊的記憶，避免記憶體重複佔用
        for i, existing_doc in enumerate(self.documents):
            if existing_doc.get('id') == doc.get('id'):
                self.documents[i] = doc
                self._rebuild_chunks() # Rebuild cache on update
                return
        self.documents.append(doc)
        # Incremental update to chunks cache
        text = doc.get('content', '')
        for i in range(0, len(text), 500):
            self.chunks.append(text[i:i+500])

    def _rebuild_chunks(self):
        """Rebuilds the entire chunks cache from documents."""
        self.chunks = []
        for d in self.documents:
            text = d.get('content', '')
            for i in range(0, len(text), 500):
                self.chunks.append(text[i:i+500])
        
    def get_scored_chunks(self, q):
        clean_q = q.replace("?", "").replace("？", "").replace(" ", "").replace("請問", "")
        q_chars = set(clean_q)
        
        # 建立長度為 2 到 4 的連續字串 (N-grams)
        ngrams = []
        for n in range(2, 5):
            if n <= len(clean_q):
                for i in range(len(clean_q) - n + 1):
                    ngrams.append(clean_q[i:i+n])
                    
        scored_chunks = []
        for chunk in self.chunks: # Use pre-cached chunks
            score = 0
            # 單一字元基本分
            score += sum(1 for char in q_chars if char in chunk)
            
            # 連續專有名詞巨大加分 (例如「水飛梭」配對成功直接加 90 分)
            for ngram in ngrams:
                count = chunk.count(ngram)
                if count > 0:
                    score += count * (len(ngram) ** 2) * 10
                    
            if score > 0:
                scored_chunks.append((score, chunk))
        return scored_chunks

class RAGEngine:
    def __init__(self):
        self.reasoner = ReasonerWrapper(llm_instance)
        # Fast Index for keyword search
        self.special_index = SimpleIndex(reasoner=self.reasoner)
        self.general_index = SimpleIndex(reasoner=self.reasoner)
        
        # Reasoning-based Tree Index (PageIndex concept)
        self.pi_storage = os.path.join(DATA_DIR, 'pageindex')
        os.makedirs(self.pi_storage, exist_ok=True)
        
    def ingest_special_data(self, documents):
        logger.info(f"Ingesting {len(documents)} special documents into Index.")
        for doc in documents:
            self.special_index.add_document(doc)
            self._background_pi_index(doc, "special")
            
    def ingest_general_data(self, documents):
        logger.info(f"Ingesting {len(documents)} general documents into Index.")
        for doc in documents:
            self.general_index.add_document(doc)
            self._background_pi_index(doc, "general")

    def _background_pi_index(self, doc, category):
        """Builds semantic reasoning trees in the background."""
        import threading
        def build():
            doc_id = doc.get('id', '')
            content = doc.get('content', '')
            if not content or len(content) < 500: return
            
            # Simple hash/check if already indexed
            target_dir = os.path.join(self.pi_storage, category)
            os.makedirs(target_dir, exist_ok=True)
            tree_file = os.path.join(target_dir, f"{os.path.basename(doc_id)}.pi.json")
            
            if os.path.exists(tree_file): return
            
            try:
                # LLM-based Summarization/Reasoning for the document
                summary_prompt = f"Analyze this medical document and create a professional summary for expert retrieval. Identify symptoms, treatments, and precautions:\n\n{content[:4000]}"
                summary = llm_instance.generate(summary_prompt, max_tokens=300)
                
                with open(tree_file, 'w', encoding='utf-8') as f:
                    json.dump({"id": doc_id, "summary": summary, "indexed_at": str(datetime.datetime.now())}, f, ensure_ascii=False)
                logger.info(f"✅ [PageIndex] Indexed reasoning tree for {os.path.basename(doc_id)}")
            except Exception as e:
                logger.error(f"PageIndex build failed for {doc_id}: {e}")
                
        threading.Thread(target=build, daemon=True).start()
            
    def query(self, question, source="special"):
        return self.query_integrated(question)

    def query_integrated(self, question):
        """
        Hybrid Reasoning:
        1. HIS Database (SQL)
        2. SimpleIndex (Keywords)
        3. PageIndex (Semantic Summaries)
        """
        logger.info(f"Integrated Hybrid Query: {question}")
        
        # 1. SQL Context
        db_path = os.path.join(DATA_DIR, 'db', 'clinic.db')
        sql_context = "無相關資料庫紀錄。"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                if any(k in question for k in ["門診", "時間", "開", "休息"]):
                    cursor.execute("SELECT day_of_week, morning_start, morning_end, afternoon_start, afternoon_end, evening_start, evening_end FROM v_clinic_hours_this_week LIMIT 7")
                    records = cursor.fetchall()
                    if records: sql_context = f"診所門診時間表:\n{records}"
                conn.close()
            except Exception as e: logger.error(f"SQL Error: {e}")

        # 2. Keyword Search (SimpleIndex)
        rag_scored_chunks = self.special_index.get_scored_chunks(question)
        rag_scored_chunks.extend(self.general_index.get_scored_chunks(question))
        rag_scored_chunks.sort(reverse=True, key=lambda x: x[0])
        
        # 3. Semantic Search (PageIndex Summaries)
        pi_context = ""
        try:
            # Quickly scan the small .pi.json files for deeper context
            summaries = []
            for cat in ["special", "general"]:
                p_dir = os.path.join(self.pi_storage, cat)
                if not os.path.exists(p_dir): continue
                # Prioritize by keyword match in summary
                for f_name in os.listdir(p_dir)[:40]:
                    if f_name.endswith(".pi.json"):
                        with open(os.path.join(p_dir, f_name), 'r') as f:
                            data = json.load(f)
                            summ = data.get('summary', '')
                            if any(k in summ for k in question[:5]):
                                summaries.append(summ)
            if summaries:
                pi_context = "【專業醫學背景參考】\n" + "\n".join(summaries[:3])
        except Exception as e: logger.warning(f"PageIndex retrieval failed: {e}")

        # Prepare Context
        top_chunks = []
        seen = set()
        for score, chunk in rag_scored_chunks:
            if chunk not in seen:
                seen.add(chunk)
                # Price Redaction
                text = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電確認]', chunk)
                text = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電確認]', text)
                top_chunks.append(text)
            if len(top_chunks) >= 3: break
                
        rag_context = "\n\n".join(top_chunks)
        
        # Combine all for LLM Reasoning
        current_date = datetime.date.today()
        messages = [
            {
                "role": "system",
                "content": f"""你是一個具備『PageIndex 深度推理』能力的專業醫美 AI 助理。
今天是 {current_date}。請綜合以下資料來精準回答。

【資料來源：診所資料庫】
{sql_context}

【資料來源：PageIndex 專業摘要】
{pi_context}

【資料來源：相關文本片段】
{rag_context}

【推理與回答準則】
1. 完全使用「繁體中文」回答，使用專業、溫暖且嚴謹的語氣。
2. 優先分析 PageIndex 摘要中的專業醫學邏輯，再結合文本片段進行細節補充。
3. 嚴格禁止報價！禁止輸出任何金錢數字。
4. 若資料有衝突，以『診所資料庫』為準，其次為『PageIndex 專業摘要』。
5. 若完全無資料，請溫柔地建議使用者親自到院諮詢，而非胡亂猜測。"""
            },
            {
                "role": "user",
                "content": question
            }
        ]
        
        return self.reasoner.reason_chat(messages).strip()
