# 第 2 階段：診所整合 - 上下文

**蒐集時間：** 2026-05-07  
**狀態：** 準備規劃

<domain>
## 階段邊界

連結診所營運與患者溝通：
- 整合本地 HIS 資料庫進行分析查詢（患者資訊、預約、用藥歷史）
- 透過 LINE 啟用患者訊息功能
- 建立患者對話歷史管理

</domain>

<decisions>
## 實作決定

### HIS 資料庫連接
- **D-01：** 當 HIS 無法使用或速度緩慢時，使用查詢佇列機制 + 自動重試。確保系統在診所 IT 不穩定時仍可靠運作。
- **D-02：** 常見 HIS 查詢（如預約、患者群組統計）使用 1 小時 TTL 快取。平衡性能與資料新鮮度。

### LINE 機器人路由
- **D-03：** LINE 查詢預設路由到 RAG（醫療知識問題）。患者問題如「血壓魅是什麼」→ RAG 搜尋醫療文件。
- **D-04：** 當 RAG 信心度 < 60% 時，自動升級給診所員工。安全臨界值，避免低信心的自動回應。

### 患者資料與上下文
- **D-05：** 患者查詢默認使用 RAG 一般知識，無需主動檢查 HIS 記錄。簡化流程，降低隱私風險。患者特定的醫療歷史由診所員工在升級流程中提供。
- **D-06：** 每位患者保留 1 週的 LINE 對話歷史。足夠長以支持多輪對話，足夠短以保護隱私。

### 升級與升級
- **D-07：** 升級給診所員工時包含整個對話歷史（該週的 LINE 對話）。給予人工完整的患者問題上下文。

</decisions>

<canonical_refs>
## 規範參考

**下游代理必須讀取這些檔案才能規劃或實作。**

### 階段要求
- `.planning/ROADMAP.md` §Phase 2 — 完整階段目標與成功標準
- `.planning/REQUIREMENTS.md` — DB-01、DB-02、DB-03、COMM-01、COMM-02、COMM-03 的 v1 需求

### 架構參考
- `src/api/routes/hybrid.py` — 現有混合查詢 API 結構（複用 SQLite 連接模式）
- `src/rag/ingest.py` — RAG 引擎初始化與查詢方法
- `src/api/app.py` — Flask 應用程式結構與路由註冊模式

### 外部整合
- LINE Messaging API 文件（用於 LINE 機器人整合）— 需要研究員探索
- HIS 資料庫架構文件（由診所 IT 提供）— 規劃階段需要確認

</canonical_refs>

<code_context>
## 現有代碼深入

### 可複用資產
- **Hybrid Query Engine** (`scripts/hybrid_query.py`)：已實作意圖分類邏輯，可複用於 LINE 訊息路由
- **SQLite 模式** (`schema/medical.db.sql`, `schema/clinic.db.sql`)：clinic.db 可擴展以存放患者對話歷史
- **RAG 查詢** (`src/api/routes/rag.py`)：已實作信心度評分，可直接用於升級判斷 (< 60%)
- **Flask API 結構** (`src/api/routes/hybrid.py`)：可作為 LINE Webhook 端點的基礎

### 已建立模式
- **API 端點設計**：使用 Blueprint 進行模組化，易於添加 LINE 機器人端點
- **錯誤處理**：hybrid.py 中的 try/except 模式可複用
- **資料驗證**：Pydantic 類型提示已在既有代碼中使用

### 整合點
- LINE Webhook 應註冊在 `src/api/app.py` 作為新 Blueprint
- HIS 查詢應使用 `scripts/hybrid_query.py` 中的快取邏輯
- 對話歷史應在 `schema/clinic.db.sql` 中新增 `patient_conversations` 表

</code_context>

<specifics>
## 特定需求

- **診所 IT 穩定性考量**：查詢佇列 + 重試機制必須在 HIS 連接故障時優雅降級
- **患者隱私**：對話歷史 1 週後自動刪除；無需主動索取 HIS 患者資訊
- **LINE 訊息流**：患者 → LINE Webhook → 意圖判斷（RAG vs. 升級） → 回應或升級

</specifics>

<deferred>
## 未來想法

- **患者個性化上下文**（Phase 3+）：在患者明確選擇時，整合 HIS 病歷至 RAG 上下文（目前保持簡單）
- **多語言支持**（Phase 3+）：目前假設繁體中文；多語言支持在未來迭代
- **高級 Hermes 整合**（Phase 4）：Hermes 代理可在升級時接手複雜查詢
- **即時 HIS 同步**（Phase 5）：目前使用快取；未來可考慮即時同步架構

</deferred>

---

*階段：02-clinic-integration*  
*上下文蒐集日期：2026-05-07*
