---
phase: 01-foundation
plan: 01
subsystem: Infrastructure Skeleton
tags: [llm, rag, flask, api]
dependency_graph:
  requires: []
  provides: [llm-server, rag-ingest, flask-api]
  affects: [Phase 2 Clinic Integration]
tech_stack:
  - llama.cpp for local LLM inference
  - Chroma for vector storage
  - Flask for REST API
  - PyPDF2 + python-docx for document parsing
key_files:
  created:
    - src/llm/server.py (LlamaCppServer class)
    - src/rag/ingest.py (DocumentIngestor class)
    - src/api/app.py (Flask app)
    - src/api/routes/inference.py
    - src/api/routes/rag.py
    - config/llama_config.json
    - config/ingest_config.json
    - requirements.txt
  modified: []
decisions:
  - D-01: Qwen 3.6 with Q8_0 quantization (10GB VRAM, target 250-300ms latency)
  - D-02: Streaming token output (real-time response building)
  - D-03: Dynamic batching based on queue depth
  - D-04: Semantic-only search via Chroma
  - D-05: Small chunks (512 tokens, 50 overlap)
  - D-06: Keep existing Chroma instance
  - D-07: Library-based parsing (PyPDF2, python-docx)
  - D-08: Flask synchronous framework
  - D-09: Full citation tracking (filename, section, page)
  - D-10: VRAM monitoring via pynvml (every 30s)
  - D-11: Token limit + queue timeout for overflow prevention
  - D-12: Daily 2AM restart for 24h stability
metrics:
  duration: "~5 minutes"
  completed_date: "2026-05-06"
---

# Phase 1 Plan 1: 基礎設施骨架 Summary

## 一行描述

本地 LLM 推理基礎設施骨架完成：llama.cpp 伺服器、Qwen 3.6 模型管理、文件攝取管道、Flask API 端點。

## 執行摘要

建立 DrtoolboxLocalServer 的基礎設施骨架，包含三個核心任務：
1. **llama.cpp 伺服器** - LlamaCppServer 類別（>100行），含模型載入、生成、串流生成、動態批次處理
2. **文件攝取管道** - DocumentIngestor 類別（>80行），支援 PDF/Word/TXT 文件解析與向量化
3. **Flask API 骨架** - Flask 應用程式（>60行），/health、/ready 健康檢查，與 inference/rag 路由

## 完成的任務

| Task | 名稱 | Commit | 檔案 |
|------|------|--------|------|
| 1 | 安裝與設定 llama.cpp 伺服器 | [hash] | src/llm/server.py, config/llama_config.json, requirements.txt |
| 2 | 建立文件攝取管道 | [hash] | src/rag/ingest.py, config/ingest_config.json |
| 3 | 建立 Flask API 骨架 | [hash] | src/api/app.py, src/api/routes/*.py |

## 驗證通過

- [x] `python -c "from src.llm.server import LlamaCppServer"` → OK
- [x] `python -c "from src.rag.ingest import DocumentIngestor"` → OK  
- [x] `python -c "from src.api.app import app"` → OK

## 與計劃的偏差

**無偏差** - 計劃完全按預期執行。

### Auto-fixed Issues

None - 計劃期間無需自動修復。

## 待完成項目

- 模型檔案下載（models/Qwen3-6B-Q8_0.gguf）
- 實際硬體測試（2080Ti GPU）
- 文件實際擷取測試

## 後續階段

本計劃為 Phase 1 的第一個計劃，完成後進入：
- Plan 02: LLM 優化與測試
- Plan 03: RAG 搜尋優化
- Plan 04: API 完整化

---

*Last updated: 2026-05-06 After Plan 01 execution*