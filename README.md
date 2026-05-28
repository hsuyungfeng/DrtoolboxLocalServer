# Drtoolbox Local Server (診所本地 AI 訓練與營運系統)

Drtoolbox 是一個專為診所設計的**隱私優先 (Privacy-First)** 本地 AI 系統。它不僅能精準回答醫療諮詢，更是一套整合了「高品質數據生產線」、「營運自動化」與「BI 決策分析」的完整解決方案。

---

## 🚀 專案目前狀態：自主成長與智慧營運階段
本專案已成功實現「數據閉環 (Data Loop)」，系統具備自我進化與深度洞察能力：
- **模型架構**：採用本地 Qwen-35B 等級模型，結合 PageIndex 語義邏輯樹實現深度醫療推理。
- **混合路由技術**：導入 **Dynamic Knowledge Fallback (動態知識回退)** 機制，平衡診所專有數據與通用醫學知識。
- **全通路對接**：支援 LINE 與 Facebook Messenger 串接，讓病患能在熟悉平台獲得 AI 服務。

---

## 🌟 核心功能描述 (Key Functions)

### 1. 🧠 動態知識路由 (Dynamic Knowledge Routing)
系統自動偵測問題類型，並採用不同的推理模式：
- **Clinic Special (診所專用路由)**：
  - **範圍**：地址、電話、營業時間、特定醫師、預約、診所特定療程項目。
  - **準則**：嚴格基於本地文件 (PageIndex + SQL) 回答，絕不胡謅，嚴禁輸出任何報價。
- **General Medicine (通用醫學路由)**：
  - **範圍**：感冒諮詢、術後保養、健康飲食、常見症狀解釋。
  - **準則**：結合本地文件與 LLM 內建的專業醫學知識庫，提供更豐富的衛教內容。

### 2. 💬 全通路病患服務 (Messaging Gateway)
- **多平台整合**：透過 Webhook 同時對接 LINE 與 Messenger。
- **安全防護網**：病患輸入「紅旗症狀」時自動攔截並發送就醫警告；偵測到「價格查詢」時自動轉向引導致電諮詢。
- **知識回流**：醫師在後端校正過的答案，會自動更新 PageIndex 推理樹，讓 AI 「越答越聰明」。

### 3. 🤖 自主數據生產線 (Auto-QA & Curation)
- **主動式 QA 生成**：每晚自動針對新療程生成高品質問答對，並提供醫師「AI 重新潤飾」功能。
- **智慧分流審核**：Dashboard 自動標註高信心回答，協助醫師在秒級時間內完成批量核准。

---

## 🛠️ 部署與使用說明 (Deployment & Usage)

### 1. 基礎啟動步驟
```bash
# 1. 確保 LLM 容器已在運行 (Port 8080)
docker start llama-qwen

# 2. 安裝依賴並啟動後端 (Port 5000)
uv sync
uv run python src/api/app.py
```

### 2. 通訊軟體對接設定 (LINE & Messenger)

#### **第一步：建立外網隧道 (Tunneling)**
由於您的伺服器在本地，雲端平台需透過隧道才能連線。
1. 安裝 [ngrok](https://ngrok.com/)。
2. 執行指令：`ngrok http 5000`。
3. 取得產生的 `https://xxxx.ngrok-free.app` 網址。

#### **第二步：LINE 設定**
1. 至 [LINE Developers](https://developers.line.biz/) 建立 **Messaging API** 頻道（需使用您的個人 LINE 帳號登入）。
2. 在 **Messaging settings** 下：
   - 將 **Webhook URL** 設定為：`https://您的隧道網址/webhook/line`。
   - 開啟 **Use webhook** 選項。
3. 在 `.env` 檔案中設定 `LINE_CHANNEL_SECRET` 與 `LINE_CHANNEL_ACCESS_TOKEN`。

#### **第三步：Facebook Messenger 設定**
1. 至 [Meta for Developers](https://developers.facebook.com/) 建立應用程式並添加 **Messenger**。
2. 在 **Webhook** 設定中：
   - **Callback URL**：`https://您的隧道網址/webhook/messenger`。
   - **Verify Token**：自訂一個字串（需與 `.env` 中的 `MESSENGER_VERIFY_TOKEN` 一致）。
3. 點擊「驗證並儲存」。

---

## ❓ 常見問題 (FAQ)

### Q: 我可以使用個人的 Facebook 或 LINE 進行測試嗎？
**可以。** 
- **LINE**：您需要建立一個「LINE 官方帳號」(LINE Official Account)，這會與您的個人帳號綁定。測試時，您可以用您的個人帳號去加這個官方帳號為好友。
- **Messenger**：您需要建立一個「Facebook 粉絲專頁」，並在 Meta 開發者後台將其與 App 綁定。測試時，您可以用您的個人帳號私訊該粉專。
- **注意**：在開發模式下，只有被您設為「Tester」的個人帳號才能收到回覆。

### Q: 隧道網址每次重啟 ngrok 都會變，怎麼辦？
在 ngrok 官網註冊免費帳號後，可以獲得一個固定的 **Static Domain**，這樣您就不需要每次都去 LINE/Meta 後台修改 Webhook URL。

---

## 🛡️ 核心運作準則
1. **路由先行**：先判斷問題類別，再決定推理強度。
2. **嚴禁報價**：絕對不輸出金錢數字。
3. **本地優先**：病患隱私與原始文件絕不上雲端。
