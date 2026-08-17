# Phase 5 Implementation Plan: Conversion, Tracking & Advanced BI

## 🎯 目標 (Objectives)
按照優先順序（2 -> 1 -> 3）提升診所 AI 的商業價值與臨床管理深度。

---

## 🏗️ 任務 1: 療程行銷轉換卡片 (Priority: 2)
**目標**：將 AI 諮詢轉化為掛號量，針對高價值療程實作精美 LINE Flex Message。

1. **擴充 `LineBeautifier`**：
    * [ ] 在 `src/services/line_beautifier.py` 新增 `build_treatment_card(treatment_name, description, image_url)`。
    * [ ] 實作 3 個核心療程模板：外泌體 (Exosomes)、皮秒雷射 (Pico)、水飛梭 (HydraFacial)。
    * [ ] 加入「一鍵撥號」與「官網看更多」按鈕。
2. **對接 Webhook 路由**：
    * [ ] 在 `src/api/routes/webhook.py` 中，根據 RAG 識別出的主題，自動觸發這些行銷卡片。

---

## 🏗️ 任務 2: 病患臨床追蹤視圖 (Priority: 1)
**目標**：讓醫師在後台能追蹤特定病患的對話歷史與修復進度。

1. **實作病患詳情 API**：
    * [ ] 在 `src/api/routes/staff_actions.py` 新增 `get_patient_profile(patient_id)`。
    * [ ] 整合該病患的所有歷史 JSONL 日誌。
2. **影像進度軸 (Timeline)**：
    * [ ] 抓取該病患上傳的所有圖片及其對應的 `🤖 AI 影像臨床分析` 筆記。
3. **前端 UI 實作**：
    * [ ] 新增 `staff_patient_detail.html`。
    * [ ] 實作「風險標記」與「紅旗警報」視覺化圖示。

---

## 🏗️ 任務 3: `ehrapy` 臨床洞察看板 (Priority: 3)
**目標**：視覺化呈現病患分群數據與知識缺口。

1. **數據導出與視覺化**：
    * [ ] 在 `src/api/routes/analytics.py` 新增 `get_clinical_insights` API，回傳 `ClinicalAnalyzer` 的 JSON 結果。
2. **Dashboard 整合**：
    * [ ] 在「營運數據」頁籤下方新增「病患表型分佈圖 (Phenotyping)」與「知識缺口預警」。
    * [ ] 使用 Chart.js 呈現分群比例。

---

## 🚀 立即啟動：實作療程行銷卡片
我將先從 **Task 1** 開始，為「外泌體」與「皮秒雷射」設計精美的 LINE 互動卡片。
