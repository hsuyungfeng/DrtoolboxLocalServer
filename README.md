# Drtoolbox Local Server (診所本地 AI 訓練與營運系統)

Drtoolbox 是一個專為診所設計的**隱私優先 (Privacy-First)** 本地 AI 系統。它不僅能精準回答醫療諮詢，更是一套整合了「高品質數據生產線」、「營運自動化」與「BI 決策分析」的完整解決方案。

---

## 🚀 專案目前狀態：自主成長與智慧營運階段
本專案已成功實現「數據閉環 (Data Loop)」，系統具備自我進化與深度洞察能力：
- **模型架構**：採用本地 Qwen-35B 等級模型，結合 **PageIndex 2.0 臨床推理樹** 實現深度醫療邏輯。
- **混合路由技術**：導入 **Dynamic Knowledge Fallback** 機制，平衡診所專有數據與通用醫學知識。
- **全通路對接**：支援 LINE 與 Messenger 串接，具備非同步處理機制與精美 Flex Message 介面。
- **數據分析**：整合 `ehrapy` 框架，實現病患數據的深度表型分析 (Deep Phenotyping)。

---

## 🌟 核心功能描述 (Key Functions)

### 1. 🧠 臨床推理樹與知識回流 (PageIndex 2.0)
- **結構化知識**：自動將文件拆解為 `術前須知`、`療程原理`、`術後照護`、`長期保養` 四大分支，大幅提升檢索精度。
- **知識回流 (Knowledge Backflow)**：醫師在後端校正過的回答會自動標記為 **「🌟 醫師權威指令」** 並注入推理樹，讓 AI 永久記住臨床標準。

### 2. 💬 專業通訊網關 (Messaging Gateway 2.0)
- **非同步處理**：解決 502 Timeout 問題，系統會立即響應並在背景完成運算後推送答案。
- **視覺美化**：自動將長回覆封裝進 **LINE Flex Message** 氣泡，並針對地址/電話提供互動式診所資訊卡。
- **安全防護網**：整合紅旗症狀偵測與報價保護機制。

### 3. 🤖 自主數據生產線 (Auto-QA & Curation)
- **主動式 QA 生成**：每晚自動掃描文獻並由 Local LLM **「背景預答」**，醫師點擊即可看到現成草案。
- **AI 校正編輯器**：支援 **「✨ AI 重新潤飾」**，可一鍵啟動聯網搜尋模式，彙整台灣最新醫學建議。

### 4. 📊 ehrapy 臨床數據洞察
- **結構化分析**：透過 `ehrapy` 分析 `clinic.db` 中的病歷數據，自動識別高風險病患分群並產出營運報告。

---

## 🛠️ 部署與使用說明 (Deployment & Usage)

### 1. 基礎啟動步驟
```bash
# 1. 確保 LLM 容器已在運行 (Port 8080)
docker start llama-qwen

# 2. 啟動後端服務 (Port 5000)
# 建議使用內建指令以確保環境變數載入
bash scripts/start_server.sh
```

### 2. 通訊軟體對接設定 (LINE & Messenger)

#### **第一步：建立外網隧道 (Tunneling)**
1. 執行指令：`ngrok http 5000`。
2. 取得產生的 `https://xxxx.ngrok-free.app` 網址。

#### **第二步：Webhook 與環境變數**
- **LINE Webhook**：`https://您的隧道網址/webhook/line`
- **Messenger Webhook**：`https://您的隧道網址/webhook/messenger`
- 請在 `.env` 中填入對應的 `CHANNEL_SECRET` 與 `ACCESS_TOKEN`。

---

## 🛠️ 維護指令 (Maintenance)

| 任務 (Task) | 指令 (Command) | 說明 (Description) |
| :--- | :--- | :--- |
| **數據分流審核** | `/dashboard/staff/approvals/` | 在後端進行數據 Triage，批量核准高品質 QA。 |
| **重整索引** | `uv run bash scripts/ingest_all.sh` | 將所有文件重新轉換為 PageIndex 2.0 樹格式。 |
| **臨床分析** | `uv run python src/services/clinical_analyzer.py` | 執行 ehrapy 病患分群分析。 |

---

## 🛡️ 核心運作準則
1. **數據權威**：醫師校正內容優先於原始文件。
2. **嚴禁報價**：絕對不透過 AI 輸出金錢數字。
3. **安全第一**：偵測到危險症狀時，強制執行人工介入導向。
