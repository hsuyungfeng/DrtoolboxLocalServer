# Drtoolbox Local Server (診所本地 AI 訓練與營運系統)

Drtoolbox 是一個專為診所設計的**隱私優先 (Privacy-First)** 本地 AI 系統。它不僅能精準回答醫療諮詢，更是一套整合了「高品質數據生產線」、「營運自動化」、「HIS 數據同步」與「BI 決策分析」的完整解決方案。

---

## 🚀 專案目前狀態：自主成長與智慧營運階段
本專案已成功實現「數據閉環 (Data Loop)」，系統具備自我進化與深度洞察能力：
- **高效 RAG 引擎 (SQLite FTS5)**：從原先的 Python 記憶體線性掃描，重構升級為 SQLite FTS5 全文索引，搭配 BM25 檢索與 fine-grained N-gram 混合排序。將 3.1 GB 大體量醫學教科書的檢索延遲從 **152+ 秒縮短至 14.06 秒 (效能提升 10 倍以上)**，徹底解決 LINE Webhook 超時斷線。
- **醫療知識圖譜 (SQLite Graph-RAG)**：將原先需要重型伺服器的 Neo4j 30 萬條關係醫療圖譜與 Jena RDF 藥物本體扁平化並導入本地 SQLite，提供零依賴的滑動窗口實體比對與多步圖譜推導引擎。
- **模型與推理樹**：採用本地 Qwen 模型，並在 SQLite 中快取 **PageIndex 2.0 臨床推理樹**，支援直接從磁碟 JSON 檔案快照遷移至資料庫，零 GPU/LLM 重建開銷。
- **HIS 深度整合**：支援本地或區域網路 (SMB) 的 HIS 資料庫 (.dbf) 自動同步，打通醫療數據孤島。
- **混合路由技術**：導入 **Dynamic Knowledge Fallback** 機制，平衡診所專有數據與通用醫學知識。
- **全通路對接**：支援 LINE 與 Messenger 串接，具備非同步處理機制與精美 Flex Message 介面。
- **行銷轉化追蹤**：具備行銷漏斗追蹤功能，精準記錄 LINE 預約轉化數據。


---

## 🌟 核心功能描述 (Key Functions)

### 1. 🏥 HIS 資料庫與 CRM 整合
- **多模式同步**：支援從本地路徑或 Windows 網路分享資料夾 (UNC) 提取 `CO03L.DBF` 資料。
- **自動網芳掃描**：一鍵掃描區域網路中開放的 HIS 資料夾，免去繁瑣的 IP 與路徑輸入。
- **病患深度視圖**：CRM 系統整合了 HIS 就診紀錄、對話歷史與 AI 風險評級。

### 2. 🚨 員工即時通知系統
- **紅旗症狀偵測**：當病患提及「流血、劇痛、發燒、呼吸困難」等高風險字眼時，系統立即觸發警示。
- **LINE 即時推送**：透過 LINE Push API 將緊急警示發送給指定員工，確保 100% 人工及時介入。

### 3. 📈 行銷漏斗與轉化分析
- **智慧預約按鈕**：LINE 行銷卡片整合 Postback 技術，追蹤每一筆「預約掛號」點擊行為。
- **轉化日誌**：自動產出轉化數據報告，幫助診所衡量 AI 行銷方案的實際轉化效果 (ROI)。

### 4. 🤖 全自動夜間自我學習 (Nightly Self-Learning)
- **定期同步與重啟**：每日凌晨自動重啟確保穩定，並同步 HIS 最新數據。
- **網實核查 (Fact-Check)**：自動檢索聯網資料，校對前日 AI 的低信心度回覆。
- **模擬提問生成**：針對新進醫療文件自動生成模擬 QA，由 AI 預擬初稿供醫師快速核閱。

### 5. 🧠 診所知識地圖與全域推理
- **視覺化知識圖譜**：透過 D3.js 呈現 AI 腦中的邏輯關聯，點擊節點即可查看相關文獻。
- **跨文件邏輯鏈 (Global Reasoning)**：分析不同文件間的協同或矛盾，產出全域臨床洞察。

### 6. 📊 Clinical CRM/BI 與疾病知識庫整合
- **ICD-10 預警分析**：系統能統計病患的 ICD-10 疾病分佈與共病風險，視覺化呈現高危險群的趨勢圖表。
- **動態衛教關懷 (Medical Advice)**：整合高達 8,800+ 種常見疾病的關聯藥物、飲食建議與檢查項目，在 Dashboard 自動產出建議卡片。
- **OTC 藥名在地化 (Drug Localization)**：系統內建高頻用藥的自動映射字典，能將艱澀的英文化學成分（如 ACETAMINOPHEN）即時對應轉譯為「普拿疼 (退燒止痛藥)」，大幅提升 AI 對話時的溝通親和力。

---

## 🛠️ 部署與使用說明 (Deployment & Usage)

### 1. 新機器全新部署步驟 (New Machine Deployment)

若要在全新機器上部署本系統，請遵循以下步驟：

#### 步驟 1：安裝系統層級依賴 (Prerequisites)
系統執行 RAG 圖文識別需要 OCR 以及底層的處理庫：
```bash
# Linux (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv sqlite3 tesseract-ocr tesseract-ocr-chi-tra

# 確保安裝 Docker（用於運行本地 LLM 推理容器）
sudo apt-get install -y docker.io
```

#### 步驟 2：複製專案與初始化虛擬環境
```bash
git clone <repository_url> DrtoolboxLocalServer
cd DrtoolboxLocalServer

# 建立並啟用 Python 3 虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝所有依賴套件
pip install --upgrade pip
pip install -r requirements.txt
```

#### 步驟 3：部署本地 LLM 推理伺服器 (Ornith)
本系統的核心推理使用本地運行的 LLM 模型。我們透過 `llama.cpp` 執行高效能模型，並支援雙顯卡分工架構：
```bash
# 載入 Ornith-1.0-9B 模型，並利用 -ts 1,0 -mg 1 參數達成
# 1060 (負責 Context) 與 3060 (負責 LLM Generation) 雙顯卡效能最佳化
/home/hsu/llama.cpp/llama-server -m /home/hsu/llama.cpp/models/Ornith-1.0-9B-UD-Q6_K_XL.gguf --port 8080 --host 0.0.0.0 -c 8192 -ngl 99 -ts 1,0 -mg 1
```

#### 步驟 4：設定環境變數 (.env)
配置根目錄下的 `.env` 檔案以確保 LINE Webhook 及本地推理管道暢通，主要設定包括：
```env
# 核心伺服器配置
PORT=5000
LLAMA_URL=http://127.0.0.1:8080/v1/chat/completions

# 外部渠道對接 (LINE & Messenger)
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token

# HIS 連線與數據庫位置
DB_PATH=data/db/clinic.db
```

#### 步驟 5：建立必要目錄與資料庫初始化
```bash
# 建立存放 RAG 文件、日誌與 SQLite 資料庫的目錄
mkdir -p data/db data/documents/special data/documents/general logs

# 初始化 SQLite 數據庫並將現有 PageIndex JSON 結構遷移匯入
python scripts/migrate_json_to_db.py
```
* **PageIndex/RAG 數據庫說明 (`data/db/rag.db`)**：
  * **`page_index_trees`**：快取與結構化儲存 PageIndex 2.0 臨床推理樹（含術前、步驟、術後短期照護與長期維持等節點，並支援醫師手動校正的筆記欄位）。搭配 FTS5 進行秒級查詢。
  * **`rag_chunks`**：快取文檔分塊，利用 FTS5 全文檢索與細粒度 N-gram 混合重排提供高關聯度文檔匹配。

#### 步驟 6：生態系一鍵啟動 (推薦)
本系統包含多個關聯服務，請使用統一腳本啟動：
```bash
# 一鍵啟動 Main Server (5000), FileBrowser (8081), Hermes API (8642)
bash scripts/start_ecosystem.sh
```

---

### 2. 排程設定 (夜間自動化學習)
請安裝 crontab 以啟用夜間自動同步與學習機制：
```bash
crontab cron/crontab.txt
```


---

## 🛠️ 維護指令 (Maintenance)

| 任務 (Task) | 指令 (Command) | 說明 (Description) |
| :--- | :--- | :--- |
| **數據量擴充** | `python scripts/expand_patient_data.py 50` | 生成 50 筆模擬病患資料用於測試。 |
| **網芳掃描** | `python scripts/scan_his_network.py` | 手動掃描區域網路中的 HIS 分享資料夾。 |
| **重整索引** | `bash scripts/ingest_all.sh` | 將所有文件重新轉換為 PageIndex 樹格式。 |
| **資料庫遷移** | `python scripts/migrate_json_to_db.py` | 將磁碟上的 PageIndex JSON 匯入 SQLite RAG 資料庫。 |
| **醫療圖譜遷移** | `python scripts/migrate_medical_graph.py` | 將 Neo4j JSON 醫療知識圖譜與 Jena RDF 藥物本體匯入 SQLite 資料庫。 |


---

## 🛡️ 核心運作準則
1. **隱私第一**：所有病患識別資料僅留存於本地 `clinic.db`。
2. **數據權威**：醫師校正內容優先於原始文件。
3. **安全防線**：偵測到危險症狀時，強制執行人工介入導向。
