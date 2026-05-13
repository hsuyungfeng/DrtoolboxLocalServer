---
phase: 06-web-dashboard
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/api/routes/system_metrics.py
  - src/templates/system_dashboard.html
  - src/api/app.py
  - src/templates/base.html
autonomous: true
requirements:
  - DASH-01
  - DASH-02
  - DASH-03
user_setup: []

must_haves:
  truths:
    - "診所員工與管理員可以視覺化地監控系統資源狀態"
    - "儀表板包含資料庫連線數、快取命中率、雲端同步狀態等關鍵指標"
  artifacts:
    - path: "src/templates/system_dashboard.html"
      provides: "系統監控儀表板"
      exports: ["GET /dashboard/system/"]
    - path: "src/api/routes/system_metrics.py"
      provides: "系統監控 API"
      exports: ["GET /api/v1/system/metrics"]
  key_links:
    - from: "src/templates/system_dashboard.html"
      to: "src/templates/base.html"
      via: "{% extends 'base.html' %}"

---

<objective>
建立系統監控儀表板 (System Dashboard)

目的：實作一個供系統管理員/技術維護人員使用的綜合儀表板網頁，集中顯示 HIS 連線池狀態、API 延遲、快取命中率以及最新的雲端同步記錄。

輸出：
- system_metrics.py (提供系統效能指標的後端 API)
- system_dashboard.html (即時更新的監控面板)
</objective>

<execution_context>
@/home/hsu/DrtoolboxLocalServer/src/db/his_connection.py
@/home/hsu/DrtoolboxLocalServer/src/db/query_cache.py
@/home/hsu/DrtoolboxLocalServer/src/api/routes/cloud_sync.py
@/home/hsu/DrtoolboxLocalServer/src/templates/base.html

現有基礎架構：
- 使用 Bootstrap 5 + Jinja2
- 已有 `clinic.db` 和 `his_connection.py` 處理連線池與快取
</execution_context>

<context>
@.planning/ROADMAP.md — Phase 6 網頁儀表板目標與需求
</context>

<tasks>

<task type="auto">
  <name>Task 1: 建立系統監控 API 路由</name>
  <files>src/api/routes/system_metrics.py</files>
  <action>
建立 `system_metrics.py` Blueprint，包含：

1. `GET /api/v1/system/metrics` — 取得系統即時狀態
   - 提取 HISConnection 的使用中連線數與可用連線數
   - 提取 QueryCache 的總快取項目與命中/未命中統計
   - 查詢最新一筆 `sync_logs` 的狀態
   - 回傳格式為 JSON
  </action>
  <verify>curl http://localhost:8080/api/v1/system/metrics 回傳完整 JSON 監控數據</verify>
  <done>系統監控 API 建立完成</done>
</task>

<task type="auto">
  <name>Task 2: 建立監控儀表板網頁 UI</name>
  <files>src/templates/system_dashboard.html</files>
  <action>
建立 `system_dashboard.html`，並繼承 `base.html`：

1. 頁面標題：「系統監控儀表板」
2. 卡片區塊 (Bootstrap Cards)：
   - **資料庫狀態**：使用中連線 / 最大連線數，連線池健康度
   - **快取狀態**：目前的快取大小 (Item Count) 與快取命中率
   - **同步狀態**：最後一次雲端同步時間與狀態
3. 使用 JavaScript (Fetch API) 每 5 秒定期呼叫 `/api/v1/system/metrics` 刷新上述卡片的數值
4. 使用 CSS 美化，數字以大字體顯示，若健康度異常(例如連線數全滿) 則卡片背景轉為警告色 (bg-warning)
  </action>
  <verify>瀏覽器訪問 /dashboard/system/ 成功顯示監控數據且每5秒自動更新</verify>
  <done>系統監控面板前端頁面完成</done>
</task>

<task type="auto">
  <name>Task 3: 註冊路由與更新導航</name>
  <files>
    - src/api/app.py
    - src/templates/base.html
  </files>
  <action>
1. 編輯 `app.py`：
   - 匯入並註冊 `system_metrics_bp`
   - 於 `_register_routes()` 中將其掛載至 app
2. 編輯 `base.html`：
   - 於頂部導航列 (Navbar) 加入新的連結：「系統監控」 (`/dashboard/system/`)
  </action>
  <verify>重啟 Flask 伺服器後，導航列出現「系統監控」且點擊正常導向</verify>
  <done>路由註冊與前端選單整合完畢</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Staff/Admin → API | 只允許員工/管理員查看系統效能與內部運作指標 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-01 | Information Disclosure | Metrics API | mitigate | 不回傳任何病患的個資或病歷內容，僅回傳資源使用量與聚合數字 |
</threat_model>

<verification>
- [ ] `system_metrics.py` 可正確提取系統內部狀態
- [ ] 存取 `/dashboard/system/` 畫面呈現完整 Bootstrap 5 版面
- [ ] Javascript 輪詢無 CORS 錯誤並能即時更新數據
</verification>

<success_criteria>
1. 儀表板頁面在 1 秒內載入完成
2. 連線數與快取項目能精準對應後端真實狀態
3. UI 具備高質感的資料視覺化 (Premium UI)
</success_criteria>

<output>
執行完成後請產出 `.planning/phases/06-web-dashboard/06-SUMMARY.md` 以紀錄成果。
</output>
