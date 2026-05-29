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

        # Load existing trees
        self._load_existing_pi_trees()
        # Worker Pool for background PageIndexing (Balanced default)
        self.pi_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="PI_Worker")
        
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
            
            data = {
                "id": doc_id, 
                "tree": tree_data, 
                "indexed_at": str(datetime.datetime.now()),
                "version": "2.0" # Clinical Reasoning Tree version
            }
            
            with open(tree_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            with self._pi_cache_lock:
                self._pi_cache.append(data)
            logger.info(f"✅ [PageIndex] Clinical Reasoning Tree ready: {os.path.basename(doc_id)}")
        except Exception as e:
            logger.error(f"PageIndex build failed for {doc_id}: {e}")
                
    def _load_existing_pi_trees(self):
        """Loads all existing .pi.json files from storage into memory cache."""
        count = 0
        for category in ["special", "general"]:
            path = os.path.join(self.pi_storage, category)
            if not os.path.exists(path): continue
            
            for file in os.listdir(path):
                if file.endswith(".pi.json"):
                    try:
                        with open(os.path.join(path, file), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            with self._pi_cache_lock:
                                self._pi_cache.append(data)
                            count += 1
                    except Exception as e:
                        logger.error(f"Failed to load tree {file}: {e}")
        logger.info(f"💾 Loaded {count} PageIndex trees into memory.")

    def query(self, question, route="special", image_data=None):
        return self.query_integrated(question, route=route, image_data=image_data)

    def inject_verified_knowledge(self, question, answer, metadata):
        """Dynamic Knowledge Backflow: Injects physician corrections into PageIndex trees."""
        logger.info(f"🔄 Injecting knowledge backflow for: {question[:30]}...")
        
        # 1. Identify which tree node this belongs to
        target_node = "procedure" # default
        if any(k in question for k in ["術前", "禁忌", "過敏", "準備"]): target_node = "pre_op"
        elif any(k in question for k in ["術後", "洗臉", "冰敷", "化妝", "休養"]): target_node = "post_op_short"
        elif any(k in question for k in ["維持", "多久", "保養", "防曬", "效果"]): target_node = "maintenance"

        # 2. Find the most relevant existing tree in cache
        # Enhanced matching: Check keywords AND file titles
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}', question)
        best_tree = None
        best_score = 0
        
        with self._pi_cache_lock:
            for item in self._pi_cache:
                if item.get('version') != "2.0": continue
                
                score = 0
                tree_text = json.dumps(item.get('tree', {}), ensure_ascii=False)
                filename = os.path.basename(item['id'])
                
                # Title weight (Highest priority)
                title_hits = sum(50 for k in keywords if k in filename)
                # Content weight
                content_hits = sum(10 for k in keywords if k in tree_text)
                
                score = title_hits + content_hits
                
                if score > best_score:
                    best_score = score
                    best_tree = item

        if best_tree and best_score >= 10:
            logger.info(f"📍 Matching tree found: {os.path.basename(best_tree['id'])} (Score: {best_score})")
            
            # Update the tree in memory
            tree = best_tree['tree']
            note_key = f"{target_node}_physician_notes"
            
            # Initialize or append to physician notes
            existing_notes = tree.get(note_key, "")
            new_note = f"【醫師校正】: {answer}"
            
            if new_note not in existing_notes:
                tree[note_key] = f"{existing_notes}\n{new_note}".strip()
                best_tree['indexed_at'] = str(datetime.datetime.now())
                
                # Persistent storage update
                try:
                    category = "special" if "/special/" in best_tree['id'] else "general"
                    target_dir = os.path.join(self.pi_storage, category)
                    tree_file = os.path.join(target_dir, f"{os.path.basename(best_tree['id'])}.pi.json")
                    with open(tree_file, 'w', encoding='utf-8') as f:
                        json.dump(best_tree, f, ensure_ascii=False, indent=4)
                    logger.info(f"💾 PageIndex tree '{tree_file}' updated with physician notes.")
                except Exception as e:
                    logger.error(f"Failed to update PageIndex storage: {e}")
        else:
            logger.warning(f"⚠️ No matching PageIndex tree found for backflow (Best Score: {best_score}). Skipping direct injection.")

    def _get_context(self, question):
        """Internal helper to gather SQL, PI, and RAG context with Physician Note priority."""
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
            # Handle version 2.0 (Reasoning Tree)
            if item.get('version') == "2.0":
                tree = item.get('tree', {})
                relevant_parts = []
                
                # Check for physician notes first in each relevant branch
                if any(k in question for k in ["術前", "禁忌", "過敏", "注意"]):
                    note = tree.get('pre_op_physician_notes')
                    if note: relevant_parts.append(f"🌟 [醫師權威指令]: {note}")
                    relevant_parts.append(f"[術前須知]: {tree.get('pre_op')}")
                
                if any(k in question for k in ["步驟", "原理", "怎麼做", "多長"]):
                    note = tree.get('procedure_physician_notes')
                    if note: relevant_parts.append(f"🌟 [醫師權威指令]: {note}")
                    relevant_parts.append(f"[療程原理]: {tree.get('procedure')}")
                
                if any(k in question for k in ["術後", "洗臉", "冰敷", "化妝", "運動"]):
                    note = tree.get('post_op_short_physician_notes')
                    if note: relevant_parts.append(f"🌟 [醫師權威指令]: {note}")
                    relevant_parts.append(f"[立即照護]: {tree.get('post_op_short')}")
                
                if any(k in question for k in ["維持", "多久打一次", "效果", "防曬"]):
                    note = tree.get('maintenance_physician_notes')
                    if note: relevant_parts.append(f"🌟 [醫師權威指令]: {note}")
                    relevant_parts.append(f"[長期保養]: {tree.get('maintenance')}")
                
                summary_text = "\n".join(relevant_parts) if relevant_parts else json.dumps(tree, ensure_ascii=False)
            else:
                # Legacy version 1.0 (Flat Summary)
                summary_text = item.get('summary', '')

            score = sum(10 for k in keywords if k in summary_text)
            if score > 0:
                pi_context_list.append((score, summary_text))
        
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

    def query_integrated(self, question, route="special", image_data=None, force_llm_knowledge=False):
        logger.info(f"Deep Hybrid Reasoning ({route}) for: {question} (image: {image_data is not None}, force_llm: {force_llm_knowledge})")
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

        if route == "special":
            # Simulation/Drafting mode fallback logic
            if force_llm_knowledge:
                not_found_instruction = "4. **找不到資料時**：若內部資料庫中沒有相關資訊，請根據你的「專業醫療與醫美知識」提供一個初步草案回答，並在回答開頭標註『[AI 預擬草案]』，供醫師後續校正。"
            else:
                not_found_instruction = "4. **找不到資料時**：若真的完全沒有關於該主題的資料，請禮貌告知：「對不起，資料庫中目前沒有該項目的特定詳細資料，建議您聯繫專業醫師以獲取精確建議。」"

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
{not_found_instruction}"""
        else:
            # General Knowledge Mode
            system_instruction = f"""你是一個專業的醫學與健康知識 AI 助理。今天是 {current_date}。
你可以結合「提供的參考資料」與你的「專業醫學知識庫」來回答使用者的健康問題。
{'如果你看到圖片，請結合圖片中的徵兆進行分析。' if image_data else ''}

【參考資料 (診所提供)】
{pi_context}
{rag_context}

【回答原則】
1. **結合知識**：如果參考資料中沒有提到，請使用你的專業醫學知識進行回答，確保資訊正確且有益。
2. **專業且繁體**：使用親切且專業的繁體中文回答。
3. **安全性**：提醒使用者你的建議僅供參考，若症狀持續應尋求醫師診斷。
4. **嚴禁報價**：絕對禁止提及任何具體價格。"""

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

        if route == "special":
            if force_llm_knowledge:
                not_found_instruction = "4. **找不到資料時**：若內部資料庫中沒有相關資訊，請根據你的「專業醫療與醫美知識」提供一個初步草案回答，並在回答開頭標註『[AI 預擬草案]』，供醫師後續校正。"
            else:
                not_found_instruction = "4. **找不到資料時**：若真的完全沒有關於該主題的資料，請告知：「對不起，資料庫中目前沒有該項目的特定詳細資料，建議您聯繫專業醫師以獲取精確建議。」"

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
4. **嚴禁報價**：絕對禁止提及任何具體價格。"""

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
