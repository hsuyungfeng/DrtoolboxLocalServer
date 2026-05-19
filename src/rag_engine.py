from src.llm_server import llm_instance
import logging

logger = logging.getLogger(__name__)

class ReasonerWrapper:
    """Wrapper to make LocalLLM compatible with reasoning interface."""
    def __init__(self, llm):
        self.llm = llm
        
    def reason(self, prompt):
        return self.llm.generate(prompt)

class SimpleIndex:
    def __init__(self, reasoner):
        self.reasoner = reasoner
        self.documents = []
        
    def add_document(self, doc):
        self.documents.append(doc)
        
    def get_scored_chunks(self, q):
        chunks = []
        for d in self.documents:
            text = d.get('content', '')
            for i in range(0, len(text), 500):
                chunks.append(text[i:i+500])
                
        clean_q = q.replace("?", "").replace("？", "").replace(" ", "").replace("請問", "")
        q_chars = set(clean_q)
        
        # 建立長度為 2 到 4 的連續字串 (N-grams)
        ngrams = []
        for n in range(2, 5):
            if n <= len(clean_q):
                for i in range(len(clean_q) - n + 1):
                    ngrams.append(clean_q[i:i+n])
                    
        scored_chunks = []
        for chunk in chunks:
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
        
    def query(self, q, secondary_index=None):
        # 合併自己與第二個資料庫的 chunks
        all_scored_chunks = self.get_scored_chunks(q)
        if secondary_index:
            all_scored_chunks.extend(secondary_index.get_scored_chunks(q))
                
        all_scored_chunks.sort(reverse=True, key=lambda x: x[0])
        
        # 為了避免雜訊，如果最高分太低，也可以視為找不到，但我們這裡先取前 3 名
        top_chunks = []
        # 過濾掉完全相同的 chunk，避免重複
        seen = set()
        for score, chunk in all_scored_chunks:
            if chunk not in seen:
                seen.add(chunk)
                top_chunks.append(chunk)
            if len(top_chunks) >= 3:
                break
        
        context = "\n\n".join(top_chunks)
        if not context:
            context = "無相關資料。"
            
        import datetime
        current_date = datetime.date.today()
        prompt = f"""<|im_start|>system
你是一個專業的醫美與診所 AI 助理。今天是 {current_date}。請根據以下提供的【參考資料】來回答使用者的問題。

【特別指示】
1. 參考資料是從圖片辨識 (OCR) 轉出的文字，可能會有錯字、排版混亂，或者沒有寫出完整的「促銷組合」四個字。
2. 只要你看到資料中有類似套餐名稱（如：XX組、XX專案）、價格標示（如：$38888），或是用加號（+）連接的多個療程項目（例如：水飛梭+肉毒），請主動將這些視為「搭配的促銷組合」並整理後回答使用者。
3. 如果參考資料中包含任何「時間線」相關的資訊（例如：治療期程、復原時間、活動優惠期間、術後追蹤時間等），請務必在回答中特別標示並詳細附上。
4. 【價格與時效限制】請嚴格檢查參考資料中標示價格或活動的時間。如果該活動或價格的時間距離今天（{current_date}）已經超過 2 個月，請直接過濾掉不要提供給使用者。只提供 2 個月內的有效價格與促銷。
5. 如果參考資料中真的完全找不到任何相關線索，才能回答「對不起，目前的資料庫中沒有關於此問題的資訊」。

【參考資料開始】
{context}
【參考資料結束】
<|im_end|>
<|im_start|>user
{q}
<|im_end|>
<|im_start|>assistant
"""
        response = self.reasoner.reason(prompt)
        # 過濾掉多餘的特殊 token
        return response.replace("<|im_end|>", "").strip()

class RAGEngine:
    def __init__(self):
        self.reasoner = ReasonerWrapper(llm_instance)
        self.special_index = SimpleIndex(reasoner=self.reasoner)
        self.general_index = SimpleIndex(reasoner=self.reasoner)
        
    def ingest_special_data(self, documents):
        logger.info(f"Ingesting {len(documents)} special documents into Index.")
        for doc in documents:
            self.special_index.add_document(doc)
            
    def ingest_general_data(self, documents):
        logger.info(f"Ingesting {len(documents)} general documents into Index.")
        for doc in documents:
            self.general_index.add_document(doc)
            
    def query(self, question, source="special"):
        """強制讓所有查詢都聯合檢索 special 和 general 兩個資料庫"""
        logger.info(f"Combined Querying for: {question}")
        # 將另一個 index 傳入進行聯合搜尋
        if source == "special":
            return self.special_index.query(question, secondary_index=self.general_index)
        else:
            return self.general_index.query(question, secondary_index=self.special_index)

    def query_integrated(self, question):
        """
        整合結構化資料庫 (SQLite) 與 非結構化知識庫 (RAG) 的查詢函式。
        同時呼叫兩種工具，再將結果合併交由 LLM 綜合回答。
        """
        logger.info(f"Integrated Querying for: {question}")
        import sqlite3
        import os
        import datetime
        from config.settings import DATA_DIR
        
        # ----------------------------------------------------
        # 1. 查詢結構化資料庫 (SQLite: clinic.db)
        # ----------------------------------------------------
        db_path = os.path.join(DATA_DIR, 'db', 'clinic.db')
        sql_context = "無相關資料庫紀錄。"
        
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 這裡建立簡單的關鍵字比對機制 (可依需求擴充)
                # 例如：如果問題提到「門診」或「時間」，我們就去查門診表
                if "門診" in question or "時間" in question or "開" in question:
                    # 查詢診所這個星期的門診時間視圖
                    cursor.execute("SELECT day_of_week, morning_start, morning_end, afternoon_start, afternoon_end, evening_start, evening_end FROM v_clinic_hours_this_week LIMIT 7")
                    records = cursor.fetchall()
                    if records:
                        sql_context = "近期門診時間表 (星期, 早上開始, 早上結束, 下午開始, 下午結束, 晚上開始, 晚上結束):\n" + str(records)
                
                # 這裡可以繼續加入其他工具（例如：查詢庫存、查詢排班等）
                
                conn.close()
            except Exception as e:
                logger.error(f"SQLite Query Error: {e}")

        # ----------------------------------------------------
        # 2. 查詢非結構化知識庫 (Chroma / RAG 向量庫)
        # ----------------------------------------------------
        rag_scored_chunks = self.special_index.get_scored_chunks(question)
        rag_scored_chunks.extend(self.general_index.get_scored_chunks(question))
        rag_scored_chunks.sort(reverse=True, key=lambda x: x[0])
        
        top_chunks = []
        seen = set()
        for score, chunk in rag_scored_chunks:
            if chunk not in seen:
                seen.add(chunk)
                top_chunks.append(chunk)
            if len(top_chunks) >= 3:
                break
                
        rag_context = "\n\n".join(top_chunks)
        if not rag_context:
            rag_context = "無相關醫療衛教資料。"

        # ----------------------------------------------------
        # 3. 組合 Prompt 給 LLM 進行綜合推論
        # ----------------------------------------------------
        current_date = datetime.date.today()
        prompt = f"""<|im_start|>system
你是一個專業的醫美與診所 AI 助理。今天是 {current_date}。
請「綜合」以下兩種資料來源（內部資料庫與醫療知識庫）來回答使用者的問題。

【資料來源一：內部診所資料庫 (如門診時間、排班、系統紀錄)】
{sql_context}

【資料來源二：醫療與活動知識庫 (OCR文本或衛教)】
{rag_context}

【回答指示】
1. 若使用者詢問診所營運（如門診時間、排班），請優先參考「內部診所資料庫」。
2. 若使用者詢問療程、價格或術後照顧，請優先參考「醫療與活動知識庫」。
3. 如果兩種來源都有提到，請巧妙地將它們整合為一篇流暢的回答。
4. 嚴格遵守：如果活動時間距離今天 ({current_date}) 已超過 2 個月，請過濾掉。將時間線（期程、復原時間等）整理清楚。
5. 請勿暴露原始資料庫格式（例如 tuple、JSON 等），請以人類自然語言解釋。
<|im_end|>
<|im_start|>user
{question}
<|im_end|>
<|im_start|>assistant
"""
        response = self.reasoner.reason(prompt)
        return response.replace("<|im_end|>", "").strip()
