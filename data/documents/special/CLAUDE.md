# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

此資料夾為**緻妍外科診所**的行銷圖文檔案庫，用於存放各類行銷素材、設計檔案與文宣資料。非程式碼專案，無建構、測試或部署流程。

## 資料夾結構

- `2025圖文/`、`2026圖IG/` — 按年度分類的社群行銷圖文（FB/IG 貼文圖片、短影音 mp4）
- `LOGO/` — 診所 Logo 檔案（PDF、JPG，含綠底/白底版本）
- `價目表/` — 醫美療程價目表（JPG 圖檔、xlsx 原始檔）
- `招牌/` — 招牌設計檔（Adobe Illustrator .ai 檔案與預覽 JPG）
- `文稿/` — 文案原稿（.docx、.pptx、.pdf）
- `洞貼膜廣告/` — 店面廣告貼膜設計圖
- `廠商PPT/` — 廠商產品簡報（.pptx、.pdf）
- `行銷合作/` — 合作廠商相關資料（YOLK、立特拉等）
- `訂購單(印刷用)/` — 印刷用訂購單（PDF 完稿、docx 原稿）
- `舊版生日卡/` — 舊版生日卡完稿（.ai、.pdf）
- `舊的圖文資料(未分類)/` — 早期未分類的圖文素材
- `地墊/` — 迎賓地墊設計檔
- `長方貼紙/` — 貼紙設計檔

## 檔案命名慣例

- 社群圖文：`{年份}_{月份}{主題}{平台}.{格式}`，例如 `2025_02冰晶水光FBIG.jpg`
- 民國年格式：`114_08水光針`（114年 = 2025年）
- 設計原稿常以 `-CS6` 標示 Illustrator 版本

## 行銷 Skill 與文案

此專案建立了 **Marketing Copywriter Skill**，用於自動生成行銷文案：

- **位置**：`~/.claude/skills/marketing-copywriter/` 與 `./marketing-copywriter/`（專案副本）
- **功能**：根據療程產品資訊，自動生成 FB / IG / LINE / TikTok 文案，支援 .docx 匯出
- **已支援療程**（5款）：
  - EMFACE 臉部電磁緊緻
  - 冰晶水光療程
  - Ellanse 膠原蛋白誘導劑
  - 肉毒療程
  - Saxenda 膳纖達體重管理
- **已生成文案**：
  - `2026圖IG/EMFACE文案/` 目錄下 EMFACE、冰晶水光、Ellanse、肉毒、Saxenda 各療程的 IG + FB 文案
  - 所有文案已匯出為 .docx，可直接複製到社群媒體使用

## 注意事項

- 所有文件以**繁體中文**為主
- 檔案包含 .ai（需 Adobe Illustrator）、.pptx、.docx、.pdf、.jpg/.png、.mp4 等格式
- 部分檔案名稱含「待定」表示尚未確認的草稿版本
- 使用 Skill 前，確認已安裝 python-docx：`pip install python-docx`
