# 診所員工使用指南

**版本**: 1.0  
**更新日期**: 2026-05-06  
**系統**: DrtoolboxLocalServer 本地 LLM + RAG 系統

---

## 目錄

1. [系統概述](#系統概述)
2. [系統需求](#系統需求)
3. [啟動系統](#啟動系統)
4. [使用方式](#使用方式)
5. [API 端點](#api-端點)
6. [常見問題](#常見問題)
7. [故障排除](#故障排除)

---

## 系統概述

DrtoolboxLocalServer 是一套本地部署的醫療文件問答系統，整合了：

- **LLM 推理引擎**: 使用 Qwen 3.6 大語言模型（本機執行，確保資料隱私）
- **RAG 向量檢索**: 對醫療文件進行語意檢索，提供相關來源引用
- **Flask API**: 提供 RESTful 接口，供診所系統串接

### 主要功能

- 自然語言詢問醫療文件內容
- 即時檢索相關文件段落
- 信心分數評估回答品質
- 完整來源引用（文件來源、章節、頁碼）

---

## 系統需求

### 硬體需求

| 項目 | 最低規格 | 建議規格 |
|------|----------|----------|
| GPU | NVIDIA RTX 2080 Ti 或同等級 | NVIDIA RTX 3090/4090 |
| VRAM | 10 GB | 24 GB |
| RAM | 16 GB | 32 GB |
| 磁碟空間 | 50 GB | 100 GB |

### 軟體需求

- Python 3.10+
- CUDA 11.8+ / CUDA 12+
- llama.cpp (已編譯)
- Chroma 向量資料庫

---

## 啟動系統

### 步驟 1: 確保環境就緒

```bash
# 確認 Python 環境
python --version  # 應該顯示 3.10+

# 確認 CUDA 可用
nvidia-smi  # 應該顯示 GPU 資訊
```

### 步驟 2: 啟動 Flask API 伺服器

```bash
# 在專案根目錄執行
python -m src.api.app
```

伺服器預設會在 `http://localhost:5000` 啟動。

### 步驟 3: 驗證系統健康

```bash
# 健康檢查
curl http://localhost:5000/health

# 回應範例：
# {
#   "status": "healthy",
#   "service": "DrtoolboxLocalServer",
#   "version": "1.0.0"
# }
```

---

## 使用方式

### 基本查詢

使用 `POST /api/v1/rag/query` 端點進行查詢：

```bash
curl -X POST http://localhost:5000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "糖尿病的治療方式是什麼？",
    "n_results": 5
  }'
```

### 回應格式

```json
{
  "answer": "糖尿病的治療主要包括以下幾個方面：1. 飲食控制...",
  "confidence": 0.85,
  "confidence_level": "high",
  "citations": [
    {
      "document_name": "糖尿病治療指南.pdf",
      "section_heading": "治療方式",
      "page_number": 3,
      "ingestion_timestamp": "2026-05-06T10:00:00Z",
      "text_snippet": "糖尿病的治療目標是..."
    }
  ],
  "sources": ["糖尿病治療指南.pdf"],
  "query_time_ms": 150.0,
  "generation_time_ms": 250.0,
  "chunks_retrieved": 5
}
```

### 欄位說明

| 欄位 | 說明 |
|------|------|
| `answer` | LLM 生成的回答 |
| `confidence` | 信心分數 (0-1)，越高表示回答越可靠 |
| `confidence_level` | 信心等級：`high` (>=0.8), `medium` (0.5-0.8), `low` (<0.5) |
| `citations` | 來源引用清單 |
| `sources` | 來源文件名稱列表 |
| `query_time_ms` | 向量檢索耗時（毫秒） |
| `generation_time_ms` | LLM 生成耗時（毫秒） |
| `chunks_retrieved` | 檢索的文件片段數量 |

---

## API 端點

### 健康檢查

| 端點 | 方法 | 說明 |
|------|------|------|
| `/health` | GET | 基本健康檢查 |
| `/ready` | GET | 就緒檢查（含依賴元件） |

### RAG 查詢

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/rag/query` | POST | RAG 查詢（包含 LLM 生成） |
| `/api/v1/rag/search` | POST | 僅向量檢索（無 LLM 生成） |
| `/api/v1/rag/ingest` | POST | 文件 ingestion |
| `/api/v1/rag/collection` | GET | 檢視 collection 資訊 |

### LLM 推理

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/generate` | POST | 標準生成 |
| `/api/v1/generate/stream` | POST | 流式生成 |

---

## 常見問題

### Q1: 如何新增醫療文件？

```bash
# 透過 API ingestion
curl -X POST http://localhost:5000/api/v1/rag/ingest \
  -F "file=@路徑/到/您的文件.pdf"
```

### Q2: 信心分數低於 0.7 怎麼辦？

1. 檢查相關文件是否已 ingestion
2. 嘗試使用更精確的關鍵詞
3. 增加 `n_results` 參數以檢索更多文件

### Q3: 回應延遲過高？

- 檢查 GPU 記憶體使用量：`nvidia-smi`
- 確認沒有其他程式佔用 GPU
- 考慮減少 `n_results` 數值

### Q4: 系統需要每天重啟嗎？

是的，系統會自動在每天凌晨 2 點重啟（由 cron 排程執行）。這是為了確保長期運作的穩定性。

---

## 故障排除

### 問題：伺服器無法啟動

**可能原因**：
- 連接埠已被佔用
- 模型檔案不存在

**解決方案**：
```bash
# 檢查連接埠
lsof -i :5000

# 確認模型檔案存在
ls -la data/models/
```

### 問題：查詢沒有回應

**可能原因**：
- LLM 模型未載入
- Chroma collection 為空

**解決方案**：
```bash
# 檢查 collection 狀態
curl http://localhost:5000/api/v1/rag/collection

# 檢查日誌
tail -f logs/app.log
```

### 問題：GPU 記憶體不足

**可能原因**：
- 模型過大
- 同時處理過多請求

**解決方案**：
1. 檢查 `config/memory_config.json` 中的閾值設定
2. 減少並發請求數量
3. 考慮使用更小的模型量化版本

---

## 技術支援

如遇無法解決的問題，請聯繫：

- 系統管理員
- 技術支援團隊

### 日誌位置

- 應用日誌：`logs/app.log`
- API 日誌：`logs/api.log`

---

*本文件最後更新於 2026-05-06*