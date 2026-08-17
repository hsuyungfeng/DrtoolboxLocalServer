# Drtoolbox Local Server (緻妍診所本地 AI 訓練與營運系統)

Drtoolbox 是一個專為診所設計的**隱私優先 (Privacy-First)**、**100% 本地端運行**的智慧醫療與營運系統。它不僅能精準回答醫療諮詢，更是一套整合了「醫療知識圖譜 (Graph-RAG)」、「臨床實體辨識 (Clinical NER)」、「病患個資去識別化 (HIPAA De-identification)」、「SOAP 語音轉錄實驗室」、「HIS 數據同步」與「BI 決策分析」的完整企業級解決方案。

---

## 🚀 專案核心亮點與架構

系統具備高隱私保護與邊緣端自我進化能力：
- **OpenMed 隱私去識別化 (HIPAA Safe Harbor)**：內建 `PrivacyService`，全方位遮蔽台灣身分證字號、手機/市話、姓名、出生年月日、病歷號 (MRN) 等敏感個資。在醫師修正訓練資料匯出時，自動進行脫敏（支援 `mask`、`replace` 合成資料、`hash` 雜湊三種模式）。
- **輕量化臨床實體識別 (Clinical NER)**：整合 `ClinicalNER` 服務，純 CPU/ONNX 毫秒級推論（不佔用顯卡 VRAM），自動從病患主訴或逐字稿中萃取 `DISEASE` (疾病/診斷)、`DRUG` (藥物/療程)、`DOSAGE` (劑量)、`FREQUENCY` (用法頻率) 與 `SYMPTOM` (症狀)，並於 SOAP Lab 前端即時渲染高辨識度臨床標籤。
- **高效 RAG 引擎 (SQLite FTS5 + PageIndex 2.0)**：結合 SQLite FTS5 全文檢索與細粒度 N-gram 混合排序，快取臨床推理樹（術前、步驟、術後短期照護與長期維持），大幅縮短檢索延遲。
- **醫療知識圖譜 (SQLite Graph-RAG)**：本地 SQLite 內建 8,800+ 種常見疾病、症狀與關聯藥物，並透過 Clinical NER 實體注入，提供零雲端依賴的滑動窗口多步圖譜推導引擎。
- **SOAP 語音轉錄與雙 LLM 擬真對比實驗室**：整合門診畫面 (DoctorConsultation) OCR 解析，一鍵從畫面提取病患姓名、生日與病歷號，並並行執行「雲端 Baseline (無 DB)」與「Local LLM (Ornith-1.0-35B + DB + Graph-RAG + NER)」的極簡專業英文 SOAP 病歷生成。
- **MITM 網路流量攔截器 (mitmproxy)**：提供 `scripts/mitm_interceptor.py` 腳本，自動攔截 `doctor-toolbox.com` 傳送的音檔與雲端 SOAP 譯文 JSON，無縫備份至本地數據庫與 A/B 對比測試。
- **OTC 藥名在地化 (Drug Localization)**：系統內建高頻用藥的自動映射字典，能將艱澀的英文化學成分（如 ACETAMINOPHEN）即時對應轉譯為「普拿疼 (退燒止痛藥)」，大幅提升臨床溝通親和力。
- **HIS 深度整合**：支援本地或區域網路 (SMB) 的 HIS 資料庫 (.dbf) 自動同步，打通醫療數據孤島。

---

## 🌟 核心模組描述 (Modules)

### 1. 🛡️ 隱私安全與資料脫敏 (`src/services/privacy_service.py`)
- **動態脫敏**：支援 `mask`、`replace`、`hash`。
- **訓練集防護**：儲存醫師校對資料至 `data/verified_training_data.jsonl` 前自動清洗。
- **RESTful API**：
  - `POST /api/dashboard/privacy/deidentify`：提供即時文本或結構化對話脫敏。
  - `GET /api/dashboard/export?anonymize=true&method=mask`：安全匯出脫敏後的微調訓練集。
  - `POST /api/dashboard/privacy/batch_clean`：一鍵批次清洗歷史訓練記錄。

### 2. 🧬 臨床 NER 與 SOAP Lab (`src/rag/clinical_ner.py`)
- **實體標註**：精準標註 5 大臨床實體類型。
- **視覺化儀表板**：SOAP 實驗室即時呈現彩色臨床標籤（🩺 疾病、💊 藥品、⚖️ 劑量、⚠️ 症狀）。
- **圖譜賦能**：實體直接注入 `GraphRAGEngine.extract_nodes_by_matching`，提升檢索召回率。

### 3. 🏥 HIS 資料庫與 CRM 整合
- **多模式同步**：支援從本地路徑或 Windows 網路分享資料夾 (UNC) 提取 `CO03L.DBF` 資料。
- **自動網芳掃描**：一鍵掃描區域網路中開放的 HIS 資料夾。
- **病患深度視圖**：CRM 系統整合了 HIS 就診紀錄、對話歷史與 AI 風險評級。

### 4. 🚨 員工即時通知系統
- **紅旗症狀偵測**：當病患提及「流血、劇痛、發燒、呼吸困難」等高風險字眼時，系統立即觸發警示。
- **LINE 即時推送**：透過 LINE Push API 將緊急警示發送給指定員工，確保 100% 人工及時介入。

---

## 🛠️ 部署與使用說明 (Deployment & Usage)

### 1. 部署步驟

#### 步驟 1：安裝系統層級依賴與 Git LFS
```bash
# Linux (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv sqlite3 tesseract-ocr tesseract-ocr-chi-tra

# 安裝 Git LFS (用於管理 clinic.db 等大型資料庫檔案)
git lfs install
```

#### 步驟 2：複製專案並拉取大檔案
```bash
git clone <repository_url> DrtoolboxLocalServer
cd DrtoolboxLocalServer

# 拉取完整資料庫 (clinic.db, medical.db)
git lfs pull
git lfs checkout
```

#### 步驟 3：初始化 Python 環境
```bash
# 推薦使用 uv 進行快速相依性管理
uv sync
```

#### 步驟 4：本地 LLM 推理伺服器配置 (Port 8080)
本系統的核心推理使用本地運行的 LLM 模型（如 `ornith-1.0-35b-Q4_K_M.gguf` 或 `Ornith-1.0-9B`），透過 Docker 或 `llama.cpp` 提供相容 OpenAI 的 API 端點：
```bash
# 驗證 Port 8080 推理伺服器
curl -s http://127.0.0.1:8080/v1/models
```

#### 步驟 5：生態系一鍵啟動
```bash
# 一鍵啟動 Main Server (5000), FileBrowser (8081), Hermes API (8642)
bash scripts/start_ecosystem.sh
```

---

## 🌐 服務端點一覽

| 服務名稱 | 預設網址 / 埠號 | 說明 |
| :--- | :--- | :--- |
| **Main Dashboard & SOAP Lab** | `http://localhost:5000` | 診所營運儀表板、SOAP 對比實驗室、CRM 分析 |
| **FileBrowser 知識庫管理** | `http://localhost:8081` | 本地醫學文檔、Special/General 資料庫管理 (免密碼) |
| **Hermes Agent API** | `http://localhost:8642` | Hermes 智能助理專用通訊介面 |
| **LLM Inference Server** | `http://localhost:8080` | 本地 llama.cpp 推理端點 (`/v1/chat/completions`) |

---

## 🧪 測試與驗證

本專案具備完整的自動化單元測試套件：
```bash
uv run env PYTHONPATH=. pytest tests/ -v
```
涵蓋測試項目：
- `tests/test_privacy_service.py`：個資脫敏、Safe Harbor、台灣身分證與電話解析。
- `tests/test_clinical_ner.py`：臨床實體辨識、處方/劑量分析與 Graph-RAG 整合。
- `tests/test_local_b2b_scraper.py`：10km 在地店家爬蟲與多通路派遣。
- `tests/test_openoutreach_bridge.py`：B2B 開發信價格防護與線索建立。
- `tests/test_rag_engine.py`：OTC 藥名本地化與衛教回覆測試。

---

## 🛡️ 核心運作與價格防護準則
1. **嚴格價格防護**：Hermes 代理人嚴禁在回覆中輸出具體金額或價格組合，若提及促銷且缺乏有效截止日期，一律引導致電診所專人諮詢。
2. **隱私第一 (Privacy-First)**：所有病患識別個資僅保存於本地端 `clinic.db`，匯出訓練集前一律自動脫敏。
3. **數據權威**：醫師校正之臨床推理筆記優先於原始文獻。
4. **安全防線**：偵測到危險紅旗症狀時，強制執行人工介入導向。
