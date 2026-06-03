# Drtoolbox Local Server (診所本地 AI 訓練與營運系統)

Drtoolbox 是一個專為診所設計的**隱私優先 (Privacy-First)** 本地 AI 系統。它不僅能精準回答醫療諮詢，更是一套整合了「高品質數據生產線」、「營運自動化」、「HIS 數據同步」與「BI 決策分析」的完整解決方案。

---

## 🚀 專案目前狀態：自主成長與智慧營運階段
本專案已成功實現「數據閉環 (Data Loop)」，系統具備自我進化與深度洞察能力：
- **高效 RAG 引擎 (SQLite FTS5)**：從原先的 Python 記憶體線性掃描，重構升級為 SQLite FTS5 全文索引，搭配 BM25 檢索與 fine-grained N-gram 混合排序。將 3.1 GB 大體量醫學教科書的檢索延遲從 **152+ 秒縮短至 14.06 秒 (效能提升 10 倍以上)**，徹底解決 LINE Webhook 超時斷線。
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

---

## 🛠️ 部署與使用說明 (Deployment & Usage)

### 1. 生態系一鍵啟動 (推薦)
本系統包含多個關聯服務，請使用統一腳本啟動：
```bash
# 啟動 Main Server (5000), FileBrowser (8081), Hermes API (8642)
bash scripts/start_ecosystem.sh
```

### 2. 基礎啟動步驟 (個別啟動)
```bash
# 1. 確保 LLM 容器已在運行 (Port 8080)
docker start llama-qwen

# 2. 啟動主後端服務 (Port 5000)
bash scripts/start_server.sh
```

### 3. 排程設定 (自動化學習)
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

---

## 🛡️ 核心運作準則
1. **隱私第一**：所有病患識別資料僅留存於本地 `clinic.db`。
2. **數據權威**：醫師校正內容優先於原始文件。
3. **安全防線**：偵測到危險症狀時，強制執行人工介入導向。
