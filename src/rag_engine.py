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

logger = logging.getLogger(__name__)

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
    def __init__(self, reasoner):
        self.reasoner = reasoner
        self.documents = []
        self.chunks = [] # Cache for faster search
        self.lock = threading.Lock() # Thread safety
        
    def add_document(self, doc):
        with self.lock:
            # 如果上傳同名檔案，直接覆蓋舊的記憶
            for i, existing_doc in enumerate(self.documents):
                if existing_doc.get('id') == doc.get('id'):
                    self.documents[i] = doc
                    self._rebuild_chunks_unlocked() 
                    return
            self.documents.append(doc)
            text = doc.get('content', '')
            for i in range(0, len(text), 400):
                self.chunks.append(text[i:i+600])

    def _rebuild_chunks_unlocked(self):
        """Rebuilds cache without acquiring lock (internal use)."""
        self.chunks = []
        for d in self.documents:
            text = d.get('content', '')
            for i in range(0, len(text), 400):
                self.chunks.append(text[i:i+600])
        
    def get_scored_chunks(self, q):
        with self.lock:
            chunks_snapshot = list(self.chunks) # Fast copy for read safety
            
        clean_q = q.replace("?", "").replace("？", "").replace(" ", "").replace("請問", "")
        q_chars = set(clean_q)
        
        ngrams = []
        for n in range(2, 6):
            if n <= len(clean_q):
                for i in range(len(clean_q) - n + 1):
                    ngrams.append(clean_q[i:i+n])
                    
        scored_chunks = []
        for chunk in chunks_snapshot:
            score = 0
            score += sum(1.5 for char in q_chars if char in chunk)
            
            for ngram in ngrams:
                count = chunk.count(ngram)
                if count > 0:
                    score += count * (len(ngram) ** 2.5) * 15
                    
            if score > 5:
                scored_chunks.append((score, chunk))
        return scored_chunks

class RAGEngine:
    def __init__(self):
        self.reasoner = ReasonerWrapper(llm_instance)
        self.special_index = SimpleIndex(reasoner=self.reasoner)
        self.general_index = SimpleIndex(reasoner=self.reasoner)
        self.pi_storage = os.path.join(DATA_DIR, 'pageindex')
        os.makedirs(self.pi_storage, exist_ok=True)
        self._pi_cache = [] 
        self._pi_cache_lock = threading.Lock()
        
        # Worker Pool for background PageIndexing (Balanced default)
        self.pi_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="PI_Worker")
        
    def ingest_special_data(self, documents):
        logger.info(f"Ingesting {len(documents)} special documents into Index.")
        for doc in documents:
            self.special_index.add_document(doc)
            self.pi_executor.submit(self._background_pi_index, doc, "special")
            
    def ingest_general_data(self, documents):
        logger.info(f"Ingesting {len(documents)} general documents into Index.")
        for doc in documents:
            self.general_index.add_document(doc)
            self.pi_executor.submit(self._background_pi_index, doc, "general")

    def _background_pi_index(self, doc, category):
        """Worker task for building semantic reasoning trees."""
        doc_id = doc.get('id', '')
        content = doc.get('content', '')
        if not content or len(content) < 300: return
        
        target_dir = os.path.join(self.pi_storage, category)
        os.makedirs(target_dir, exist_ok=True)
        tree_file = os.path.join(target_dir, f"{os.path.basename(doc_id)}.pi.json")
        
        if os.path.exists(tree_file): 
            try:
                with open(tree_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    with self._pi_cache_lock:
                        self._pi_cache.append(data)
            except: pass
            return
        
        try:
            summary_prompt = f"Analyze this medical/clinic document and create an exhaustive professional summary. Focus on procedures, recovery, risks, and clinical advice:\n\n{content[:5000]}"
            summary = llm_instance.generate(summary_prompt, max_tokens=512)
            
            data = {"id": doc_id, "summary": summary, "indexed_at": str(datetime.datetime.now())}
            with open(tree_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            with self._pi_cache_lock:
                self._pi_cache.append(data)
            logger.info(f"✅ [PageIndex] Reasoning tree ready: {os.path.basename(doc_id)}")
        except Exception as e:
            logger.error(f"PageIndex build failed for {doc_id}: {e}")
                
    def query(self, question, source="special", image_data=None):
        return self.query_integrated(question, image_data=image_data)

    def _get_context(self, question):
        """Internal helper to gather SQL, PI, and RAG context."""
        # 1. SQL
        db_path = os.path.join(DATA_DIR, 'db', 'clinic.db')
        sql_context = "無相關資料庫紀錄。"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                if any(k in question for k in ["門診", "時間", "開", "休息", "排班"]):
                    cursor.execute("SELECT day_of_week, morning_start, morning_end, afternoon_start, afternoon_end, evening_start, evening_end FROM v_clinic_hours_this_week LIMIT 7")
                    records = cursor.fetchall()
                    if records: sql_context = f"診所門診時間表:\n{records}"
                conn.close()
            except Exception as e: logger.error(f"SQL Error: {e}")

        # 2. PageIndex (Semantic Memory)
        pi_context_list = []
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', question) 
        with self._pi_cache_lock:
            cache_snapshot = list(self._pi_cache)
        for item in cache_snapshot:
            summary = item.get('summary', '')
            score = sum(10 for k in keywords if k in summary)
            if score > 0:
                pi_context_list.append((score, summary))
        pi_context_list.sort(reverse=True, key=lambda x: x[0])
        pi_context = "\n\n".join([x[1] for x in pi_context_list[:5]])
        if not pi_context: pi_context = "無相關深度推理摘要。"

        # 3. SimpleIndex
        rag_scored_chunks = self.special_index.get_scored_chunks(question)
        rag_scored_chunks.extend(self.general_index.get_scored_chunks(question))
        rag_scored_chunks.sort(reverse=True, key=lambda x: x[0])
        top_chunks = []
        seen = set()
        for score, chunk in rag_scored_chunks:
            if chunk not in seen:
                seen.add(chunk)
                text = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電確認]', chunk)
                text = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電確認]', text)
                top_chunks.append(text)
            if len(top_chunks) >= 8: break 
        rag_context = "\n\n".join(top_chunks)
        if not rag_context: rag_context = "無相關原始文本片段。"
        
        return sql_context, pi_context, rag_context

    def query_integrated(self, question, image_data=None):
        logger.info(f"Deep Hybrid Reasoning for: {question} (image: {image_data is not None})")
        sql_context, pi_context, rag_context = self._get_context(question)
        
        # 1. First, get the answer
        current_date = datetime.date.today()
        if image_data:
            user_content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        else:
            user_content = question

        messages = [
            {
                "role": "system",
                "content": f"""你是一個具備頂尖『PageIndex 深度推理』能力的專業醫美與診所 AI 助理。今天是 {current_date}。
你的任務是從提供的資料中「挖掘」出最精確長度之醫學與術後建議。
{'如果你看到圖片，請結合圖片中的臨床徵兆進行分析。' if image_data else ''}

【核心資料來源：PageIndex 專業摘要 (具備高層次邏輯)】
{pi_context}

【輔助資料來源：原始文本片段 (具備細節)】
{rag_context}

【基礎資料來源：診所資料庫 (營運相關)】
{sql_context}

【專業回答指南】
1. **嚴禁簡體中文**：全程必須使用繁體中文，且口氣要專業、親切、具備權威性。
2. **優先權**：若 PageIndex 摘要中有提到具體醫學流程或術後原則，請優先採用。若原始片段有補充細節，請一併整合。
3. **禁止報價**：絕對不能出現任何金錢數字、價格、特價資訊。遇到價格一律引導致電診所。
4. **細節補充**：請儘可能整理成條列式，讓使用者一眼就能看到重點（如冰敷時間、禁忌食物等）。
5. **找不到資料時**：若真的完全沒有關於該主題的資料，請不要胡謅。請禮貌告知：「對不起，資料庫中目前沒有該項目的特定詳細資料，建議您聯繫專業醫師以獲取精確建議。」"""
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        answer = self.reasoner.reason_chat(messages).strip()

        # 2. Ask LLM to evaluate its own confidence based on the provided context
        eval_prompt = f"""請針對你剛才的回答（問題：『{question}』）進行「資料依賴度」評分。

評分邏輯：
- 100分：答案完全精準對應資料來源中的每一點。
- 80分：答案核心來自資料來源，但有些微輔助詞來自常識。
- 50分：資料來源模糊，你主要靠通用醫學知識推論。
- 10分：資料來源完全無關，你是純靠通用知識回答。

請僅回傳一個數字（如 95 或 40），不要有任何其他文字說明。"""
        
        try:
            score_res = llm_instance.generate(eval_prompt, max_tokens=10).strip()
            if "<think>" in score_res: score_res = score_res.split("</think>")[-1].strip()
            # Find all digits in the response
            digits = re.findall(r'\d+', score_res)
            confidence_score = int(digits[0]) if digits else 50
        except Exception as e:
            logger.error(f"Scoring error: {e}")
            confidence_score = 50 
            
        return answer, confidence_score

    def query_integrated_stream(self, question, image_data=None):
        logger.info(f"Deep Hybrid Reasoning (Stream) for: {question} (image: {image_data is not None})")
        sql_context, pi_context, rag_context = self._get_context(question)
        
        current_date = datetime.date.today()
        
        # Multimodal Content
        if image_data:
            user_content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        else:
            user_content = question

        messages = [
            {
                "role": "system",
                "content": f"""你是一個具備頂尖『PageIndex 深度推理』能力的專業醫美與診所 AI 助理。今天是 {current_date}。
你的任務是從提供的資料中「挖掘」出最精確長度之醫學與術後建議。
{'如果你看到圖片，請結合圖片中的臨床徵兆進行分析。' if image_data else ''}

【核心資料來源：PageIndex 專業摘要 (具備高層次邏輯)】
{pi_context}

【輔助資料來源：原始文本片段 (具備細節)】
{rag_context}

【基礎資料來源：診所資料庫 (營運相關)】
{sql_context}

【專業回答指南】
1. **嚴禁簡體中文**：全程必須使用繁體中文，且口氣要專業、親切、具備權威性。
2. **優先權**：若 PageIndex 摘要中有提到具體醫學流程或術後原則，請優先採用。若原始片段有補充細節，請一併整合。
3. **禁止報價**：絕對不能出現任何金錢數字、價格、特價資訊。遇到價格一律引導致電診所。
4. **細節補充**：請儘可能整理成條列式，讓使用者一眼就能看到重點（如冰敷時間、禁忌食物等）。
5. **找不到資料時**：若真的完全沒有關於該主題的資料，請不要胡謅。請禮貌告知：「對不起，資料庫中目前沒有該項目的特定詳細資料，建議您聯繫專業醫師以獲取精確建議。」"""
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
        eval_prompt = f"""針對剛才的回答（內容摘要：{full_answer[:200]}...），請評估其對『資料來源』的依賴程度。
請給出 1 到 100 的信心分數。只需回傳純數字。"""
        try:
            score_res = llm_instance.generate(eval_prompt, max_tokens=10).strip()
            if "<think>" in score_res: score_res = score_res.split("</think>")[-1].strip()
            confidence_score = int(re.search(r'\d+', score_res).group())
        except:
            confidence_score = 50
            
        yield f"__CONFIDENCE_SCORE__{confidence_score}"
