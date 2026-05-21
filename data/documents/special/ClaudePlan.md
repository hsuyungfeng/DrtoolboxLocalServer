# ClaudePlan — 行銷圖文檔案整理專案計畫

## 目標

建立一套 Claude Code Skill，用於緻妍外科診所的行銷文案生成與管理。

## 階段規劃

### 第一階段：建立行銷文案 Skill（marketing-copywriter）

- [x] 需求確認與腦力激盪
- [x] Skill 架構設計
- [x] 建立 Skill 核心檔案（SKILL.md）
- [x] 建立診所基本資訊（references/clinic-info.md）
- [x] 建立平台語氣規範（references/platform-guide.md）
- [x] 建立第一個產品知識庫：EMFACE（references/product-kb/emface.md）
- [x] 建立 .docx 匯出腳本（scripts/export_docx.py）— 已測試通過
- [x] 實測：用 EMFACE 資料產生 IG + FB + LINE 文案（含圖片嵌入 .docx）
- [x] 更新 platform-guide.md 加入 LINE 規範
- [x] 升級 export_docx.py 支援圖片嵌入
- [x] 複製 Skill 至專案根目錄
- [x] TikTok 動態圖文影片（React 互動版 + MP4 渲染版）
- [x] platform-guide.md 加入 TikTok 規範
- [x] 打包 Skill（marketing-copywriter.tar.gz）
- [x] 為 TikTok 影片加入背景音樂（EMFACE_TikTok_with_music.mp4）
- [x] 擴充產品知識庫（冰晶水光、Ellanse、肉毒、Saxenda 4款療程）
- [x] 為 4 種療程生成完整行銷文案（IG + FB 各一份，共 8 份文案）

### 第二階段（進行中）

- [x] 圖文素材管理功能 — 建立 `服務項目/` 樹狀目錄，16 個服務各有獨立子目錄
  - 每個服務：`廠商資料/` + `行銷素材/` + `文案/` + `README.md`（含 Q&A）
  - 整理 2026圖IG/ UUID 未命名檔案（分類至 Saxenda文案/ 和廠商PPT/Belotero）
  - 總索引：`服務項目/INDEX.md`（服務比較表 + 跨服務 Q&A）
  - **新增**：粉瘩移除療程、表皮囊腫移除、寧顏提升療（血漿成纖維）3 個服務項目
- [x] 舊圖文資料(未分類) 清理
  - 詳細分析 140+ 個未分類 IMG 檔案
  - 識別並移動有效美學療程素材（6 個檔案至新服務項目）
  - 刪除已停醫療程序檔案（5 個痔瘡/大腸鏡相關檔案）
  - **新增**：完整分類 140+ 舊檔案到 `行銷素材/` 目錄結構
    - 原始素材庫：109 個（IMG_* 格式，2023年9月批量匯入）
    - 已停用素材：15 個（2022年舊 Facebook 截圖）
    - 診所活動：6 個（派對、生日慶祝、活動傳單）
    - 療程示範素材：2 個（Saxenda 相關）
    - 院內資料：3 個（QR Code）
    - 廢棄檔案：隱藏目錄存檔
  - 清空舊圖文資料(未分類)目錄，全部資料已分類
- [ ] 行銷排程建議功能（根據節日、季節推薦療程）
- [ ] 為其他療程生成 LINE + TikTok 文案（冰晶水光、Ellanse、肉毒、Saxenda）
- [ ] 構建文案版本管理系統（追蹤更新歷史）
- [ ] 審查並分類原始素材庫中的 109 個檔案到相應療程目錄

## 設計決策

| 決策 | 選擇 | 原因 |
|------|------|------|
| Skill 位置 | `~/.claude/skills/marketing-copywriter/` | 跨專案重複使用 |
| 輸出格式 | 純文字 / Markdown / .docx 皆支援 | 彈性最大 |
| 語氣策略 | 依平台自動調整（IG 輕鬆、FB 專業） | 符合實際行銷需求 |
| 產品知識庫 | 每療程一個 .md 檔案 | 按需載入，節省 context |
