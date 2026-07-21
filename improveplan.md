# DrtoolboxLocalServer 雙圖譜融合與整合升級方案 (Multi-Graph Integration Plan)

本方案針對 **DrtoolboxLocalServer** (基於國產推理引擎與 SQLite 的緻妍診所 RAG 系統) 與以下兩大醫療知識問答系統，以及 **SoapVoice** 醫療語音病歷系統進行深度整合：
1. **`chatbot-base-on-Knowledge-Graph`** (以下簡稱 **Neo4j 系統**)：基於 Neo4j 圖資料庫的 30 萬關係醫療圖譜。
2. **`KGQA-Based-On-medicine`** (以下簡稱 **Jena/REfO 系統**)：基於 Apache Jena Fuseki 三元組庫及 REfO (Regular Expression for Objects) 物件正則表達式的問答系統。
3. **`SoapVoice`** (以下簡稱 **SoapVoice 系統**)：基於本地 LLM 與 Whisper 的醫療語音轉 SOAP 結構化病歷系統。

---

## 1. 三方架構對比與分析 (Comparative Analysis)

| 維度 | DrtoolboxLocalServer | Neo4j / Jena 系統 | SoapVoice 系統 |
| :--- | :--- | :--- | :--- |
| **圖數據與資料庫** | 關係型 SQLite 表 (`medical_nodes`/`edges`) | `medical.json` (Neo4j) / TTL RDF (Jena) | SQLite (`medical.db`) 含 9.6 萬 ICD-10、1.2 萬藥品、2102 醫囑 |
| **核心功能** | 診所營運、患者諮詢與客服資料採集 | 臨床疾病、症狀、用藥圖譜推導 | 語音轉文字 (Whisper) 與 結構化 SOAP 病歷生成 |
| **外部依賴** | **極低** (僅需 SQLite，純 Python) | **高** (需 Neo4j 服務 / Java Fuseki) | **極低** (FastAPI, Whisper.cpp/Faster-Whisper) |
| **回答生成器** | 本地 LLM (Qwen-35B) 整合生成 | 模板句式拼接 (Brittle Templates) | 本地 LLM (Gemma-4/Qwen) 生成標準化病歷 |

---

## 2. 核心整合策略：雙圖譜融合與語音病歷模組 (Core Integration Strategy)

為了保持系統的 **「零依賴、全本地化、高響應度」** 特色，我們將：
1. **雙圖譜融合**：離線將 Neo4j JSON 及 Jena RDF 數據庫拍平導入本地 SQLite `clinic.db` 中。
2. **導入 SoapVoice 豐富資料集**：將 SoapVoice 擁有的 9.6 萬條 ICD-10 診斷代碼、1.2 萬條臨床藥品、2,102 條醫療處置醫囑及 1,665 條病歷範本直接併入 `clinic.db` 或作為獨立的檢索源，極大豐富「一般醫學資料」與臨床推薦能力。
3. **引進語音轉 SOAP 功能**：在 Curation Web Dashboard 中新增「語音病歷生成」分頁，調用 SoapVoice 的 API 或者是 Whisper 模組，讓診所醫生或助理可直接用語音錄製病患狀況，自動生成結構化的 SOAP (Subjective, Objective, Assessment, Plan) 病歷。

```mermaid
graph TD
    %% 數據源
    subgraph 數據與臨床資源融合 (Database Integration)
        NeoData[Neo4j Json / medical.json] --> DB[(clinic.db <br> medical_nodes / edges)]
        JenaData[Jena TTL / kgdrug.ttl] --> DB
        SoapDb[SoapVoice medical.db <br> ICD-10 / 藥物 / 處置] --> DB
    end

    %% 功能入口
    subgraph 門診 CRM 與助理 (CRM & Voice Modules)
        User[患者/醫生語音] --> ASR[Whisper / 語音轉文字]
        ASR --> SOAP[SOAP 結構化生成模組]
        SOAP --> PatientProfile[病患 CRM Profile]
        
        Chat[文字諮詢] --> Router{意圖路由器}
        Router -->|醫療/用藥| DB
        Router -->|病患歷程| PatientProfile
    end
    
    %% 生成回覆
    DB --> Context[組裝圖譜自然語言上下文]
    Context --> LLM[本地 Llama-Server 推理]
    LLM --> Out[緻妍診所智慧醫療助理回覆]
    SOAP --> LLM
```

---

## 3. 具體整合步驟 (Implementation Roadmap)

### 🚀 第一步：使用 RDFlib 進行 TTL 數據遷移 (RDF to SQLite)
在 `scripts/migrate_jena_graph.py` 中，使用 `rdflib` 庫解析 Jena 系統的本體文件 `kgdrug.ttl`，轉換為三元組格式並寫入 `clinic.db` 的 `medical_nodes` 與 `medical_edges` 中。

### 🚀 第二步：合併 SoapVoice 醫學資料庫 (ICD-10 & Drugs)
將 SoapVoice 的 `data/local_db/medical.db` 資料庫表結構，直接附加 (ATTACH) 並合併至 `clinic.db`：
1. **`icd10_codes`**：提供 96,802 條標準疾病診斷代碼。
2. **`drugs`**：提供 12,042 條常見藥品數據，用於與圖譜推薦藥物做實體對齊。
3. **`medical_orders`**：提供 2,102 條標準醫囑處置。
這些標準字典將作為 RAG 分詞檢索與推薦藥物合法性比對的黃金標準數據。

### 🚀 第三步：改進問句解析 (Porting REfO Patterns to GraphRAGEngine)
Jena 系統使用 `refo` 進行模板匹配（例如匹配「疾病有什麼症狀」）。我們在 `src/rag/graph_rag_engine.py` 中加入一個輕量級的**規則匹配器**：
1. **分詞與詞性標記**：使用 `jieba.posseg` 將問題標記為 `nj` (疾病)、`nd` (藥物)、`nz` (症狀) 等詞性。
2. **規則比對**：若符合特定規則（例如出現「批准文號」、「療效」），直接觸發對應的 SQLite SPARQL-like 語句，快速找出精準屬性。

### 🚀 第四步：新增「語音病歷/SOAP 生成」服務 (Voice to SOAP Endpoint)
1. **FastAPI 橋接**：在 `src/api/routes/` 下新增 `soap_bridge.py` 路由。
2. **ASR 語音辨識**：串接本地的 `Faster-Whisper` 或是直接呼叫本地啟動的 `SoapVoice` 後台端點 (`/api/v1/clinical/soap/generate`)。
3. **病患 CRM 聯動**：生成之 SOAP 病歷可一鍵存入 `clinic.db` 的病患病歷追蹤表中，大幅簡化診所後台人工輸入病歷的負擔。

### 🚀 第五步：安全防禦與引導 (Redaction & Compliance)
* 整合多方系統的藥品與文號數據時，必須特別小心。一旦涉及**自費療程報價或活動諮詢**，在 context 注入 LLM 之前，必須經由 `rag_engine.py` 的 Regex 進行嚴格過濾與**價格屏蔽**，統一使用引導文字，引導至診所專人諮詢。

### 🚀 第六步：醫療問答本地化與醫病互動優化 (Medical Localization & Interactive Engagement)
為了提升問答的實用性與醫病信任感，系統在輸出醫療常識回答時將進行以下優化：
1. **非處方藥名稱本地化 (OTC Drug Localization)**：
   * 在提及通用醫療學名時，自動補充台灣民眾熟悉的常用俗稱。例如：將「乙醯胺酚」轉化或註記為「**俗稱普拿疼的乙醯胺酚**」，將「布洛芬」註記為「**常見的布洛芬**」，提高患者閱讀時的理解度。
2. **與診所預約機制結合 (Appointment CTA Integration)**：
   * 在觸發高風險「紅旗症狀」或給出關鍵診斷預防資訊的段落後，自動注入臨床就醫指引與導流按鈕。例如：
     > 「若您有上述紅旗症狀，或是頭痛已影響日常，建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。」
3. **主動式醫病互動 (Patient Engagement)**：
   * 於醫學常識回答的結尾，系統會根據病症特徵自動追問細節以進行分流。例如在頭痛回答結尾主動詢問患者頭痛的「**部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素**」，收集更完整的病歷上下文以利轉接人工或輔助醫生診斷。

---

## 4. 系統融合後的預期效果 (Expected Outcomes)

1. **臨床級精準度**：結合了 30 萬條知識關係與 9.6 萬條 ICD-10 代碼，當患者或醫生查詢特定病症時，AI 能提供高度精確的學術和臨床資訊。
2. **智慧診所助手 (Voice-to-SOAP)**：系統從單純的「線上客服與資料採集」升級為「客服＋智慧門診助理」，醫生可以直接通過語音口述，由小妍在後台生成標準的 SOAP 結構化病歷，存入 HIS 系統。
3. **零外部依賴與隱私保障**：所有 ASR（語音識別）、SOAP 生成、圖譜查詢及 LLM 推理均在診所本地（GPU/CPU）運行，完全符合 HIPAA 與醫療隱私合規規範。
