---
phase: 05-enterprise-features
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/templates/base.html
  - src/templates/analytics_dashboard.html
  - src/api/routes/analytics.py
autonomous: true
requirements:
  - SYNC-02
  - WEB-03
user_setup: []

must_haves:
  truths:
    - "員工可以查看診所分析儀表板"
    - "分析數據包含患者統計、訊息趨勢、排班資訊"
    - "所有模板繼承統一的 base.html"
  artifacts:
    - path: "src/templates/base.html"
      provides: "統一基礎模板"
      min_lines: 80
    - path: "src/templates/analytics_dashboard.html"
      provides: "分析儀表板頁面"
      exports: ["GET /dashboard/analytics/"]
    - path: "src/api/routes/analytics.py"
      provides: "分析數據 API"
      exports: ["GET /api/v1/analytics/*"]
  key_links:
    - from: "src/templates/analytics_dashboard.html"
      to: "src/templates/base.html"
      via: "{% extends 'base.html' %}"
      pattern: "extends.*base\\.html"
    - from: "src/api/routes/analytics.py"
      to: "src/templates/analytics_dashboard.html"
      via: "render_template"
      pattern: "render_template.*analytics"
---

<objective>
建立統一基礎模板與分析儀表板

目的：擴充現有 Bootstrap 5 + Jinja2 模板系統，新增基礎模板供後續頁面重用，並建立診所分析儀表板展示關鍵指標。

輸出：
- base.html（統一導航、樣式、Bootstrap 5）
- analytics_dashboard.html（分析儀表板頁面）
- analytics.py（分析數據 API）
</objective>

<execution_context>
@/home/hsu/DrtoolboxLocalServer/src/templates/staff_dashboard.html
@/home/hsu/DrtoolboxLocalServer/src/templates/staff_inbox.html
@/home/hsu/DrtoolboxLocalServer/src/api/app.py

# 現有模板 Pattern 參考：
- 使用 Bootstrap 5.1.3 CDN
- 語系：zh-TW（繁體中文）
- 樣式變數：--primary-color, --danger-color, --success-color
- Jinja2 繼承結構
</execution_context>

<context>
@.planning/ROADMAP.md — Phase 5 目標與需求
@.planning/PROJECT.md — 診所資訊平台願景
</context>

<tasks>

<task type="auto">
  <name>Task 1: 建立統一的 base.html 基礎模板</name>
  <files>src/templates/base.html</files>
  <action>
建立 base.html 基礎模板，包含：
1. Bootstrap 5.1.3 CDN 引入
2. 統一導航欄（診所名稱、儀表板、患者、收件箱、分析）
3. 樣式變數定義（--primary-color, --danger-color, --success-color, --warning-color, --gray-light）
4. 通用樣式（body, container, 卡片陰影）
5. 頁腳版權資訊
6. Jinja2 block 結構：{% block title %}, {% block content %}, {% block scripts %}

注意：
- 語系使用 zh-TW（繁體中文）
- 導航連結應包含：/dashboard/staff/patients（患者）、/dashboard/staff/inbox（收件箱）、/dashboard/analytics（分析）
- 預設背景色：#f8f9fa
- 容器最大寬度：1200px
  </action>
  <verify>base.html 存在且包含 Bootstrap 5 CDN、導航欄、block 結構</verify>
  <done>base.html 建立完成，後續頁面可繼承此模板</done>
</task>

<task type="auto">
  <name>Task 2: 建立分析數據 API 路由</name>
  <files>src/api/routes/analytics.py</files>
  <action>
建立 analytics.py Blueprint，包含以下 API：

1. GET /api/v1/analytics/overview — 診所概覽數據
   - 返回：總患者數、本月新患者、本月訊息數、待處理升級數

2. GET /api/v1/analytics/messages — 訊息趨勢數據
   - 返回：過去 7 天每日訊息數、頻道分布（LINE/網頁）

3. GET /api/v1/analytics/patients — 患者統計數據
   - 返回：患者年齡分布、依賴度分布（高/中/低）

4. GET /api/v1/analytics/appointments — 預約統計
   - 返回：今日預約、本週預約、完成率

實作細節：
- 使用現有 clinic.db 資料庫連線
- 從 patients、appointments、messages 表查詢數據
- 返回 JSON 格式，包含 timestamp 欄位
- 適當的錯誤處理，回傳 500 時有有意義的錯誤訊息
  </verify>
  <verify>curl http://localhost:8080/api/v1/analytics/overview 返回 JSON 數據</verify>
  <done>分析 API 可提供診所關鍵指標數據</done>
</task>

<task type="auto">
  <name>Task 3: 建立分析儀表板頁面</name>
  <files>src/templates/analytics_dashboard.html</files>
  <action>
建立 analytics_dashboard.html，使用 {% extends 'base.html' %}：

1. 繼承 base.html 的統一導航與樣式
2. 頁面標題：「診所分析儀表板」

2. 區塊規劃：
   - 概覽卡片區（4 格）：總患者、本月新患者、本月訊息、待處理升級
   - 訊息趨勢圖表區（Chart.js 折線圖）
   - 患者統計區（年齡分布長條圖）
   - 預約統計區（今日/本週預約數據）

3. JavaScript 功能：
   - 頁面載入時 fetch /api/v1/analytics/* 數據
   - 使用 Chart.js 渲染趨勢圖表
   - 自動更新：每 60 秒刷新數據

4. 樣式要求：
   - 卡片使用 Bootstrap .card 元件
   - 間距使用 .g-4（gap-4）格狀排列
   - 數字使用大字体（font-size: 32px）強調
   - 載入中顯示 spinner，錯誤顯示 alert

注意：所有文字使用繁體中文，圖表標籤使用中文
  </verify>
  <verify>訪問 /dashboard/analytics/ 顯示儀表板頁面，包含 4 個數據卡片與圖表</verify>
  <done>分析儀表板完整顯示診所關鍵指標</done>
</task>

<task type="auto">
  <name>Task 4: 註冊 Analytics Blueprint 到 Flask App</name>
  <files>src/api/app.py</files>
  <action>
在 app.py 的 _register_routes() 函數中新增：

1. 匯入 analytics blueprint：
   ```python
   from api.routes.analytics import analytics_bp
   ```

2. 註冊 blueprint：
   ```python
   app.register_blueprint(analytics_bp)
   ```

3. 新增根路由資訊：
   在 root() 的 endpoints 中新增：
   ```python
   "analytics": "/api/v1/analytics/*",
   "analytics_page": "/dashboard/analytics/"
   ```
  </verify>
  <verify>Flask 啟動無錯誤，/dashboard/analytics/ 路由可訪問</verify>
  <done>Analytics 路由已註冊並可正常訪問</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client→API | 瀏覽器客戶端獲取分析數據 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-01 | Information Disclosure | analytics API | mitigate | 僅提供聚合統計數據，無原始患者敏感資訊 |
| T-05-02 | Denial of Service | analytics endpoints | accept | 定時快取避免過度查詢，適當超時 |
</threat_model>

<verification>
- [ ] base.html 包含 Bootstrap 5 CDN 與導航欄
- [ ] analytics_dashboard.html 正確繼承 base.html
- [ ] /api/v1/analytics/overview 返回正確 JSON
- [ ] 儀表板頁面顯示 4 個數據卡片
- [ ] Chart.js 圖表正確渲染
- [ ] 所有文字為繁體中文
</verification>

<success_criteria>
1. 員工訪問 /dashboard/analytics/ 可看到完整的分析儀表板
2. 數據卡片顯示：總患者數、本月新患者、本月訊息數、待處理升級數
3. 圖表顯示訊息趨勢（過去 7 天）
4. 所有模板使用統一的 base.html
5. API 回應時間 < 1 秒
</success_criteria>

<output>
完成後建立 `.planning/phases/05-enterprise-features/05-01-SUMMARY.md`
</output>

---

---
phase: 05-enterprise-features
plan: 02
type: execute
wave: 2
depends_on: ["05-01"]
files_modified:
  - src/templates/staff_approvals.html
  - src/templates/staff_appointments.html
  - src/templates/staff_messages.html
  - src/api/routes/staff_actions.py
autonomous: true
requirements:
  - COMM-05
  - SYNC-02
user_setup: []

must_haves:
  truths:
    - "員工可以批准/拒絕患者升級請求"
    - "員工可以管理預約（新增、修改、取消）"
    - "員工可以發送訊息給患者"
  artifacts:
    - path: "src/templates/staff_approvals.html"
      provides: "升級審批頁面"
      exports: ["GET /dashboard/staff/approvals/"]
    - path: "src/templates/staff_appointments.html"
      provides: "預約管理頁面"
      exports: ["GET /dashboard/staff/appointments/", "POST /api/v1/appointments/"]
    - path: "src/templates/staff_messages.html"
      provides: "訊息發送頁面"
      exports: ["POST /api/v1/messages/send"]
    - path: "src/api/routes/staff_actions.py"
      provides: "員工操作 API"
      exports: ["POST /api/v1/escalations/*", "POST /api/v1/appointments/*", "POST /api/v1/messages/send"]
  key_links:
    - from: "src/templates/staff_approvals.html"
      to: "src/templates/base.html"
      via: "{% extends 'base.html' %}"
    - from: "src/api/routes/staff_actions.py"
      to: "src/services/escalation_handler.py"
      via: "import"
    - from: "src/api/routes/staff_actions.py"
      to: "src/services/message_router.py"
      via: "import"
---

<objective>
建立員工互動功能

目的：擴充員工操作能力，支援升級審批、預約管理、訊息發送等功能。

輸出：
- staff_approvals.html（升級審批頁面）
- staff_appointments.html（預約管理頁面）
- staff_messages.html（訊息發送頁面）
- staff_actions.py（員工操作 API）
</objective>

<execution_context>
@/home/hsu/DrtoolboxLocalServer/src/templates/base.html
@/home/hsu/DrtoolboxLocalServer/src/templates/staff_inbox.html
@/home/hsu/DrtoolboxLocalServer/src/services/escalation_handler.py

# 現有服務 Pattern 參考：
- 使用 PatientService 進行資料庫操作
- 使用 MessageRouter 發送訊息
- 返回 JSON 格式響應
</execution_context>

<context>
@.planning/ROADMAP.md — Phase 5 目標與需求
@.planning/phases/05-enterprise-features/05-01-SUMMARY.md — Wave 1 完成內容
</context>

<tasks>

<task type="auto">
  <name>Task 1: 建立員工操作 API（staff_actions.py）</name>
  <files>src/api/routes/staff_actions.py</files>
  <action>
建立 staff_actions.py Blueprint，包含以下 API：

1. 升級處理 API：
   - GET /api/v1/escalations/list — 取得所有待處理升級列表
   - POST /api/v1/escalations/<id>/approve — 批准升級
   - POST /api/v1/escalations/<id>/reject — 拒絕升級
   - POST /api/v1/escalations/<id>/assign — 指派處理人員

2. 預約管理 API：
   - GET /api/v1/appointments/list — 取得預約列表（可篩選日期範圍）
   - POST /api/v1/appointments/create — 建立新預約
   - PUT /api/v1/appointments/<id> — 更新預約
   - DELETE /api/v1/appointments/<id> — 取消預約

3. 訊息發送 API：
   - POST /api/v1/messages/send — 發送訊息給患者
   - POST /api/v1/messages/broadcast — 廣播訊息（可選）

實作細節：
- 需要 X-Staff-ID header 驗證員工身份
- 使用 clinic.db 的 appointments 表
- 訊息發送使用現有 MessageRouter 服務
- 所有操作記錄 audit trail（created_by, updated_by）
- 返回適當的 HTTP 狀態碼（200, 201, 400, 404）
  </verify>
  <verify>curl -X GET http://localhost:8080/api/v1/escalations/list 返回 JSON 列表</verify>
  <done>員工操作 API 可處理升級、預約、訊息</done>
</task>

<task type="auto">
  <name>Task 2: 建立升級審批頁面</name>
  <files>src/templates/staff_approvals.html</files>
  <action>
建立 staff_approvals.html，使用 {% extends 'base.html' %}：

1. 頁面標題：「升級審批」
2. 功能區塊：
   - 待處理升級列表（表格顯示：患者名稱、升級原因、申請時間、操作）
   - 已批准/已拒絕歷史標籤頁

3. 表格欄位：
   - 患者姓名（連結至患者詳情）
   - 升級原因（文字）
   - 申請時間（格式：YYYY-MM-DD HH:mm）
   - 操作（批准按鈕、拒絕按鈕）

4. JavaScript 功能：
   - 點擊批准/拒絕按鈕呼叫 API
   - 成功後重新載入列表
   - 載入中顯示 spinner
   - 錯誤顯示 Bootstrap alert

5. 樣式：
   - 使用 Bootstrap table-striped
   - 批准按鈕：.btn-success（綠色）
   - 拒絕按鈕：.btn-danger（紅色）
   - 頁面路徑：/dashboard/staff/approvals/
  </verify>
  <verify>訪問 /dashboard/staff/approvals/ 顯示升級列表與審批按鈕</verify>
  <done>員工可以批准或拒絕患者升級請求</done>
</task>

<task type="auto">
  <name>Task 3: 建立預約管理頁面</name>
  <files>src/templates/staff_appointments.html</files>
  <action>
建立 staff_appointments.html，使用 {% extends 'base.html' %}：

1. 頁面標題：「預約管理」
2. 功能區塊：
   - 日期選擇器（可選擇查看日期範圍）
   - 預約列表（表格：患者姓名、日期時間、狀態、操作）
   - 新增預約表單（Modal）

2. 表格欄位：
   - 患者姓名（可搜尋）
   - 預約日期時間
   - 狀態（pending/confirmed/completed/cancelled）
   - 操作（編輯、取消）

3. 新增預約 Modal 表單：
   - 患者選擇（下拉選單或搜尋）
   - 日期時間選擇器
   - 備註欄位

4. JavaScript 功能：
   - 日期篩選功能
   - CRUD 操作（使用 API）
   - 狀態顏色標籤（pending=黃色, confirmed=藍色, completed=綠色, cancelled=灰色）
   - 頁面路徑：/dashboard/staff/appointments/
  </verify>
  <verify>訪問 /dashboard/staff/appointments/ 顯示預約列表與新增表單</verify>
  <done>員工可以新增、編輯、取消預約</done>
</task>

<task type="auto">
  <name>Task 4: 建立訊息發送頁面</name>
  <files>src/templates/staff_messages.html</files>
  <action>
建立 staff_messages.html，使用 {% extends 'base.html' %}：

1. 頁面標題：「發送訊息」
2. 功能區塊：
   - 患者選擇區（下拉選單或搜尋患者）
   - 訊息內容編輯區（文字輸入，可選 Markdown 支援）
   - 發送選項（LINE/網頁/兩者）
   - 發送按鈕

3. 表單欄位：
   - 患者選擇（必填）
   - 訊息內容（必填，最大 1000 字）
   - 發送頻道（預設：LINE）
   - 是否需要回覆追蹤（checkbox）

4. JavaScript 功能：
   - 患者搜尋（fetch /api/patients/search）
   - 發送前確認對話框
   - 成功顯示 Toast 通知
   - 錯誤顯示 Alert

5. 樣式：
   - 使用 Bootstrap form-floating
   - 發送按鈕：.btn-primary
   - 頁面路徑：/dashboard/staff/messages/send
  </verify>
  <verify>訪問 /dashboard/staff/messages/send 顯示訊息發送表單</verify>
  <done>員工可以發送訊息給患者</done>
</task>

<task type="auto">
  <name>Task 5: 註冊 Staff Actions Blueprint</name>
  <files>src/api/app.py</files>
  <action>
在 app.py 的 _register_routes() 中新增：

1. 匯入 staff_actions blueprint：
   ```python
   from api.routes.staff_actions import staff_actions_bp
   ```

2. 註冊 blueprint：
   ```python
   app.register_blueprint(staff_actions_bp)
   ```
  </verify>
  <verify>Flask 啟動無錯誤，所有新路由可訪問</verify>
  <done>Staff Actions 路由已註冊</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| staff→API | 員工執行升級審批、預約管理、訊息發送 |
| API→MessageRouter | 訊息發送至外部 LINE 系統 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-03 | Tampering | staff_actions API | mitigate | 驗證 X-Staff-ID header，操作記audit log |
| T-05-04 | Elevation of Privilege | escalations approve | mitigate | 僅管理層可批准升級（待擴充權限系統） |
| T-05-05 | Spoofing | message send | mitigate | 訊息內容過濾敏感資訊，記錄發送者 |
</threat_model>

<verification>
- [ ] /api/v1/escalations/list 返回升級列表
- [ ] /api/v1/appointments/list 返回預約列表
- [ ] /dashboard/staff/approvals/ 顯示升級審批頁面
- [ ] /dashboard/staff/appointments/ 顯示預約管理頁面
- [ ] /dashboard/staff/messages/send 顯示訊息發送頁面
- [ ] 所有操作返回正確的 HTTP 狀態碼
</verification>

<success_criteria>
1. 員工可以查看並批准/拒絕升級請求
2. 員工可以管理預約（新增、編輯、取消）
3. 員工可以發送訊息給患者
4. 所有操作記audit trail
5. 錯誤處理完善，有友好的錯誤訊息
</success_criteria>

<output>
完成後建立 `.planning/phases/05-enterprise-features/05-02-SUMMARY.md`
</output>

---

---
phase: 05-enterprise-features
plan: 03
type: execute
wave: 3
depends_on: ["05-02"]
files_modified:
  - src/api/routes/cloud_sync.py
  - schema/clinic.db.sql
  - src/services/cloud_sync_service.py
autonomous: true
requirements:
  - SYNC-01
  - SYNC-02
user_setup:
  - service: doctor-toolbox.com
    why: "雲端同步目標服務"
    env_vars:
      - name: CLOUD_SYNC_URL
        source: "doctor-toolbox.com 帳戶設定"
      - name: CLOUD_SYNC_API_KEY
        source: "doctor-toolbox.com API 金鑰"

must_haves:
  truths:
    - "患者資料可同步至 doctor-toolbox.com"
    - "分析數據可同步至雲端儀表板"
    - "同步狀態可追蹤與監控"
  artifacts:
    - path: "src/api/routes/cloud_sync.py"
      provides: "雲端同步 API 端點"
      exports: ["POST /api/v1/sync/patient", "POST /api/v1/sync/analytics", "GET /api/v1/sync/status"]
    - path: "src/services/cloud_sync_service.py"
      provides: "雲端同步服務"
      exports: ["sync_patient_data", "sync_analytics_data", "get_sync_status"]
    - path: "schema/clinic.db.sql"
      provides: "同步記錄表"
      contains: "sync_logs"
  key_links:
    - from: "src/api/routes/cloud_sync.py"
      to: "src/services/cloud_sync_service.py"
      via: "import"
    - from: "src/services/cloud_sync_service.py"
      to: "clinic.db"
      via: "sync_logs table"
---

<objective>
建立雲端同步基礎設施

目的：實作與 doctor-toolbox.com 的雙向資料同步，包含患者資料與分析數據的同步功能。

輸出：
- cloud_sync.py（雲端同步 API）
- cloud_sync_service.py（同步服務層）
- sync_logs 表（同步記錄）
- schema migrations
</objective>

<execution_context>
@/home/hsu/DrtoolboxLocalServer/src/services/patient_service.py
@/home/hsu/DrtoolboxLocalServer/src/db/his_connection.py
@/home/hsu/DrtoolboxLocalServer/src/api/routes/analytics.py

# 現有服務 Pattern 參考：
- 使用配置管理環境變數
- 記錄操作日誌
- 錯誤處理與重試機制
</execution_context>

<context>
@.planning/ROADMAP.md — Phase 5 SYNC-01, SYNC-02 需求
@.planning/phases/05-enterprise-features/05-02-SUMMARY.md — Wave 2 完成內容
</context>

<tasks>

<task type="auto">
  <name>Task 1: 建立同步記錄 Schema（Migrations）</name>
  <files>schema/clinic.db.sql</files>
<action>
在 clinic.db.sql 末尾新增 sync_logs 表：

```sql
-- ============================================================================
-- Cloud Sync Tables (雲端同步)
-- ============================================================================

-- 同步記錄表
CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,  -- 'patient', 'analytics', 'appointment'
    direction TEXT NOT NULL,   -- 'push' (local->cloud), 'pull' (cloud->local)
    status TEXT NOT NULL,     -- 'pending', 'completed', 'failed'
    record_id TEXT,           -- 同步記錄的 ID
    payload_json TEXT,        -- 同步資料的 JSON
    error_message TEXT,       -- 錯誤訊息（失敗時）
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 同步狀態索引
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_type ON sync_logs(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_logs_created ON sync_logs(created_at);

-- 同步配置表
CREATE TABLE IF NOT EXISTS sync_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

注意：
- 使用現有的 clinic.db（不是新建）
- 使用 SQLite 的 AUTOINCREMENT
- 包含重試計數欄位（retry_count）
- 預設 created_at 為 CURRENT_TIMESTAMP
  </verify>
  <verify>SQL 語法正確，clinic.db 可成功更新</verify>
  <done>同步記錄表已建立，可追蹤同步狀態</done>
</task>

<task type="auto">
  <name>Task 2: 建立雲端同步服務（cloud_sync_service.py）</name>
<files>src/services/cloud_sync_service.py</files>
<action>
建立 cloud_sync_service.py，包含：

1. 同步配置：
   - CLOUD_SYNC_URL（doctor-toolbox.com API URL）
   - CLOUD_SYNC_API_KEY（API 金鑰）
   - SYNC_INTERVAL（同步間隔，預設 5 分鐘）

2. 主要功能：
   - sync_patient_data(patient_id) — 同步單一患者資料至雲端
   - sync_analytics_data() — 同步分析數據至雲端儀表板
   - get_sync_status() — 取得同步狀態
   - process_pending_syncs() — 處理待同步的記錄

3. 同步邏輯：
   - 患者資料同步（push）：將本地患者資料推送至 doctor-toolbox.com
   - 分析數據同步（push）：將聚合統計數據推送至雲端儀表板
   - 記錄每次同步操作至 sync_logs 表

4. 錯誤處理：
   - 網路錯誤：記錄失敗，重試最多 3 次
   - 衝突處理：本地優先，記錄衝突
   - 日誌記錄：使用 logging 模組

實作注意：
- 使用 requests 庫進行 HTTP 呼叫
- 設定 timeout（30 秒）
- 快取 API key（勿記錄到日誌）
  </verify>
  <verify>cloud_sync_service.py 可正常 import，無語法錯誤</verify>
  <done>雲端同步服務可處理患者與分析數據同步</done>
</task>

<task type="auto">
  <name>Task 3: 建立雲端同步 API 路由</name>
<files>src/api/routes/cloud_sync.py</files>
<action>
建立 cloud_sync.py Blueprint，包含：

1. 患者資料同步 API：
   - POST /api/v1/sync/patient — 同步單一患者至雲端
   - POST /api/v1/sync/patients/bulk — 批量同步患者

2. 分析數據同步 API：
   - POST /api/v1/sync/analytics — 手動觸發分析數據同步

3. 同步狀態 API：
   - GET /api/v1/sync/status — 取得同步狀態
   - GET /api/v1/sync/logs — 取得同步日誌

4. 配置 API：
   - GET /api/v1/sync/config — 取得同步配置
   - PUT /api/v1/sync/config — 更新同步配置

API 設計細節：
- 需要管理員權限（未來可擴充）
- 返回格式：{success: bool, sync_id: int, message: str}
- 錯誤返回：{error: str, code: str}
- 響應header包含 request_id（追蹤用）

Stub 實作：
- 由於 doctor-toolbox.com API 尚未實作，這些 endpoint 目前會：
  - 記錄sync_log 到資料庫（status='completed'）
  - 返回模擬成功響應
  - 日誌記錄「Cloud sync stub — 實際同步將在 production 環境啟用」
  </verify>
  <verify>Flask 啟動時 Blueprint 成功註冊</verify>
  <done>雲端同步 API 已建立（Stub 模式）</done>
</task>

<task type="auto">
<name>Task 4: 註冊 Cloud Sync Blueprint</name>
  <files>src/api/app.py</files>
<action>
在 app.py 的 _register_routes() 中新增：

1. 匯入 cloud_sync blueprint：
   ```python
   from api.routes.cloud_sync import cloud_sync_bp
   ```

2. 註冊 blueprint：
   ```python
   app.register_blueprint(cloud_sync_bp)
   ```

3. 新增根路由資訊：
   在 root() 的 endpoints 中新增：
   ```python
   "sync_patient": "/api/v1/sync/patient",
   "sync_analytics": "/api/v1/sync/analytics",
   "sync_status": "/api/v1/sync/status"
   ```
  </verify>
  <verify>Flask 啟動無錯誤，/api/v1/sync/* 路由可訪問</verify>
  <done>Cloud Sync 路由已註冊</done>
</task>

<task type="auto">
<parameter name="Task 5: 更新 base.html 導航欄加入同步狀態</name>
  <files>src/templates/base.html</files>
  <action>
在 base.html 導航欄中新增「雲端同步」連結：

1. 導航項目：<a href="/dashboard/staff/sync">雲端同步</a>
2. 位置：放在「分析」之後

3. 可選：新增同步狀態指示器
   - 顯示最後同步時間
   - 同步失敗警告（紅點）

注意：此為 Wave 3 的最後任務，依賴前面任務完成
  </verify>
  <verify>base.html 導航包含「雲端同步」連結</verify>
  <done>導航欄已更新，可訪問同步頁面</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local→cloud | 本地資料推送至 doctor-toolbox.com |
| cloud→local | 雲端資料下載至本地（未來擴充） |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-06 | Information Disclosure | sync API | mitigate | 敏感欄位過濾，不傳輸密碼/病歷細節 |
| T-05-07 | Tampering | sync payload | mitigate | API key 驗證，payload 雜湊校驗 |
| T-05-08 | Repudiation | sync logs | mitigate | 所有同步操作記錄至 sync_logs 表 |
| T-05-09 | Availability | cloud endpoint | accept | Stub 模式，網路失敗不影響本地運作 |
</threat_model>

<verification>
- [ ] sync_logs 表建立成功
- [ ] /api/v1/sync/patient 返回成功響應（stub）
- [ ] /api/v1/sync/analytics 返回成功響應（stub）
- [ ] /api/v1/sync/status 返回同步狀態
- [ ] base.html 導航包含「雲端同步」連結
- [ ] 同步日誌記錄到資料庫
</verification>

<success_criteria>
1. 患者資料可記錄同步日誌（stub 模式）
2. 分析數據可觸發同步（stub 模式）
3. 同步狀態可查詢
4. 同步記錄可追蹤
5. 環境變數配置正確（CLOUD_SYNC_URL, CLOUD_SYNC_API_KEY）
</success_criteria>

<output>
完成後建立 `.planning/phases/05-enterprise-features/05-03-SUMMARY.md`
</output>