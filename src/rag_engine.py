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
                
        q_words = set(q.replace("?", "").replace("？", "").replace(" ", ""))
        scored_chunks = []
        for chunk in chunks:
            score = sum(1 for char in q_words if char in chunk)
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
            
        prompt = f"""<|im_start|>system
你是一個專業的醫美與診所 AI 助理。請「嚴格」根據以下提供的【參考資料】來回答使用者的問題。
如果參考資料中沒有明確的答案，請回答「對不起，目前的資料庫中沒有關於此問題的資訊」，絕對不可捏造、猜測或使用你原本的預訓練知識。

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
