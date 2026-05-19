# 專案目錄結構與資料庫生命週期指南 (Directory & Data Structure Guide)

本文件詳細說明了 **DrtoolboxLocalServer** 的整體目錄結構，特別針對核心的 `@data` 目錄進行深入剖析，以利臨床系統維護人員理解資料庫的流向、原始文件管理，以及 AI 模型微調數據的收集機制。

---

## 1. 專案根目錄結構 (Root Directory Overview)

以下為專案的根目錄架構：

```text
DrtoolboxLocalServer/
├── .planning/           # 專案進度追蹤與 GSD 工作串流狀態紀錄
├── config/              # 系統配置檔目錄 (包含 Flask 後端設定與 Llama-server 參數)
├── cron/                # 定時任務 (例如夜間自動同步、CRM 分析腳本)
├── data/                # 🌟 本地資料核心目錄 (資料庫、原始文件、對話日誌與微調集)
├── scripts/             # 維護與診所排班、營銷數據同步、知識庫重建之工具腳本
├── src/                 # 主要應用程式原始碼
│   ├── agent/           # Hermes 路由決策代理人 (Router) 與對話代理人
│   ├── api/             # Flask 路由接口 (/api/chat, /api/dashboard)
│   ├── database/        # 結構化資料庫 SQL 連接層與資料處理
│   ├── static/          # 前端網頁靜態資源 (CSS 樣式, JavaScript 交互邏輯)
│   └── templates/       # HTML 前端模板 (Glassmorphism 玻璃擬物暗黑主題)
└── tests/               # 單元測試與 API 整合測試套件
```

---

## 2. 核心資料夾 `@data` 深入剖析 (Deep Dive into `/data`)

`data/` 目錄是本專案的「資料心臟」，實行 **隱私優先 (Privacy-First)** 的本地儲存架構。以下是詳細的子目錄層級：

```text
data/
├── db/                                # 結構化與向量化資料庫
│   ├── clinic.db                      # 🟢 主診所資料庫 (包含每週排班、門診時段視圖)
│   ├── medical.db                     # 🟢 統一醫學與文檔分塊資料庫 (已整合原 case_templates.db 與 chunks)
│   ├── chroma_rag/                    # 🟢 Chroma 向量資料庫目錄 (儲存非結構化嵌入向量)
│   └── archive_legacy/                # 🟡 歷史備份與優化歸檔目錄
│       └── clinic_local.db            # 歷史快取資料庫
├── documents/                         # 原始非結構化文件 (Ingestion 來源)
│   ├── general/                       # 一般醫學常識、大眾衛教宣傳 PDF/TXT/CSV
│   └── special/                       # 診所敏感檔案、專屬主治醫師簡介、內部價格表
├── filebrowser/                       # 系統檔案管理器存儲與 AstraBot 分享暫存區
├── models/                            # 本地模型快取或 GGUF 符號連結 (核心模型放在外部)
├── interactions_YYYY-MM-DD.jsonl      # 每日對話互動日誌 (自動收集微調數據)
└── verified_training_data.jsonl       # 經醫師/專家人工審查並導出的黃金微調數據集
```

---

## 3. 各資料庫元件功能與用途說明 (Database Components)

### 3.1 結構化資料庫 (`data/db/*.db`)
1. **`clinic.db` (主要)**
   * **用途**：紀錄診所的營運狀態、每週醫生排班、看診時段。
   * **與 AI 串接**：`src/agent/hermes_router.py` 在執行混合查詢 (`query_integrated`) 時，會直接調用並獲取該資料庫的目前週次排班視圖 (`v_clinic_hours_this_week`)。這能確保 AI 回答門診時間時具有 **100% 的事實準確性 (Zero-Hallucination)**。
2. **`medical.db` (統一醫學通用資料庫 - 已整合)**
   * **用途**：將原本分散的 `medical.db`（包含醫學術語對照、病歷模板、病理特徵）與 `case_templates.db`（1665 條文檔分塊 `chunks` 及其 embedding 向量）進行完美合併。
   * **包含表與視圖**：`medical_knowledge` (醫療知識)、`medical_conditions` (病理症狀)、`medical_treatments` (臨床治療)、`case_templates` (病歷引導模板)、`chunks` (知識文檔分塊) 等。這提供了一個多用途、高擴展性的臨床與通用醫學知識庫中心。

### 3.2 非結構化資料庫與文件 (`data/documents/` 與 `data/db/chroma_rag/`)
1. **原始文件目錄 (`data/documents/`)**
   * **`general/`**：存放如一般消化系外科常見問題、術後保養等通識文件。
   * **`special/`**：存放高敏感度資訊。例如 **「主治醫師學經歷背景」**、**「最新未公開價格表與營銷規範」**。
2. **向量資料庫 (`data/db/chroma_rag/`)**
   * **技術**：ChromaDB。
   * **流程**：當診所人員在 Dashboard 上傳文件時，後端會啟動背景執行緒，利用 OCR (如 PDF 解析或 Tesseract 圖片辨識) 提取文字，將其切分成區塊 (Chunking)，並透過 Embedding 模型轉化為向量存入此目錄。
   * **查詢**：當用戶提問非結構化問題（如：「醫師有看過員基醫院嗎？」），RAG 引擎會在此進行語意相似度檢索。

---

## 4. 對話日誌與 AI 模型微調生命週期 (Feedback Loop & Fine-tuning)

本系統的核心價值之一是 **自動收集高品質的本地微調數據**，這完全依賴於日誌結構的設計。

### 4.1 每日互動日誌 (`data/interactions_YYYY-MM-DD.jsonl`)
系統中的每次對話，皆會即時以 JSON Lines (JSONL) 格式記錄至 `data/` 下。每條記錄包含極為詳盡的中介數據：
* `timestamp`: 對話時間戳記。
* `user_message`: 用戶的原始繁體中文輸入。
* `route_used`: 決策路由 (`sql` 查詢、`rag` 檢索、或 `general` 一般推理)。
* `retrieved_context`: 
  * 若走 `sql` 路由：記錄從 `clinic.db` 實際查出的 JSON 數據（如醫師排班元組）。
  * 若走 `rag` 路由：記錄從 ChromaDB 檢索到的 Top-K 原始文本區塊。
* `llm_prompt`: 送入 `llama-server` 的最終完整 Prompt (包含注入的上下文資訊)。
* `llm_reply`: AI 最终生成的回覆。
* `latency_seconds` 與 `tokens_used`: 生成耗時與 Token 消耗量。

### 4.2 黃金訓練集導出 (`data/verified_training_data.jsonl`)
* **機制**：當診所醫生或系統管理員在 Web Dashboard 的「對話歷史與優化」分頁中，針對某個 AI 回答給予 **「正向反饋 (Thumbs Up)」**，或者對錯誤回答進行 **「人工修正 (Human Correction)」** 時，該筆記錄會被標記並寫入 `verified_training_data.jsonl`。
* **用途**：該檔案即為診所專屬的 **黃金對話微調數據集 (Golden Dataset)**，可直接用於對下一代 Gemma/Qwen 模型進行 LoRA 微調，打造愈用愈聰明的專科 AI。

---

## 5. 資料結構優化重組提案 (Reorganization Proposal)

為了保持目錄的乾淨與易讀性，建議執行以下優化重組（Reorganization）：

1. **建立封存目錄**：
   將無直接引用的備份資料庫搬移至獨立的歸檔資料夾，避免與正式運作的 `clinic.db` 混淆。
   ```bash
   mkdir -p data/db/archive_legacy
   mv data/db/clinic_local.db data/db/archive_legacy/
   mv data/db/medical.db data/db/archive_legacy/
   ```

2. **建立自動備份策略**：
   在 `cron/` 目錄中配置每晚將 `clinic.db` 與 `interactions_*.jsonl` 壓縮備份至 `data/backups/`，確保臨床數據絕對安全。

3. **統一上傳入口**：
   診所員工所有新上傳的文件，由 Dashboard API 自動分流寫入 `data/documents/special/` (需高強度加密或本地權限控管) 與 `data/documents/general/`。
