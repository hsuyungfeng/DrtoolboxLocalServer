---
phase: 01-foundation
plan: 03
subsystem: Monitoring & Citations
tags: [gpu, memory, rag, citations, daily-restart]
dependency_graph:
  requires: [Plan 02 (complete)]
  provides: [gpu-monitoring, confidence-scores, source-citations, daily-restart]
  affects: [Phase 2 Clinic Integration]
tech_stack:
  - pynvml for GPU monitoring
  - Chroma for vector search
  - Flask for REST API
  - Cron for scheduled restarts
key_files:
  created:
    - config/memory_config.json (memory monitoring config)
    - scripts/daily_restart.sh (daily restart script)
    - cron/crontab.txt (cron schedule)
  modified:
    - src/llm/server.py (add memory monitoring methods)
    - src/api/routes/rag.py (expand with citation response)
    - src/rag/query.py (existing methods verified)
decisions:
  - D-10: nvidia-smi + pynvml (GPU monitoring)
  - D-11: Token limit + queue timeout (stream stop)
  - D-12: 2 AM daily restart
metrics:
  duration: "~5 minutes"
  completed_date: "2026-05-06"
---

# Phase 1 Plan 3: 監控與引用 Summary

## 一行描述

GPU 記憶體監控（30秒輪詢、18GB 警報）、RAG 信心分數與來源引用、每日凌晨 2 點自動重啟機制實作完成。

## 執行摘要

完成 Plan 03 三個核心任務：

1. **Task 7: GPU 記憶體監控** - 在 `src/llm/server.py` 新增 `init_nvml()`、`get_gpu_memory()`、`check_memory_threshold()` 方法，以及背景記憶體監控執行緒（30秒輪詢）。建立 `config/memory_config.json` 設定檔，warning threshold 18GB，critical threshold 20GB。

2. **Task 8: RAG 信心分數與來源引用** - 驗證現有 `calculate_confidence()` 和 `format_citations()` 方法正常運作。更新 `src/api/routes/rag.py` 使用 QueryAnswer 類別，回應格式包含 answer、confidence、confidence_level、citations（包含 document_name、section_heading、page_number、ingestion_timestamp）。

3. **Task 9: 每日重啟機制** - 建立 `scripts/daily_restart.sh` 腳本（ graceful shutdown、SIGTERM + force kill fallback、cache clear、health check）。建立 `cron/crontab.txt` 排程（每日凌晨 2 點）。

## 完成的任務

| Task | 名稱 | Commit | 檔案 |
|------|------|--------|------|
| 7 | GPU 記憶體監控 | 2fa4618 | src/llm/server.py, config/memory_config.json |
| 8 | RAG 信心分數與來源引用 | c512cad | src/rag/query.py (已存在), src/api/routes/rag.py |
| 9 | 每日重啟機制 | 095ff75 | scripts/daily_restart.sh, cron/crontab.txt |

## 驗證通過

- [x] `python -c "from src.llm.server import LlamaCppServer; s=LlamaCppServer(); print('has get_gpu_memory:', hasattr(s,'get_gpu_memory')); print('has check_memory_threshold:', hasattr(s,'check_memory_threshold'))"` → True, True
- [x] `python -c "from src.rag.query import QueryAnswer; qa=QueryAnswer(); print('has calculate_confidence:', hasattr(qa,'calculate_confidence')); print('has format_citations:', hasattr(qa,'format_citations'))"` → True, True
- [x] `ls -la scripts/daily_restart.sh` → exists + executable

## 與計劃的偏差

**無偏差** - 計劃完全按照 PLAN.md 執行。

所有 must-haves 實現：
- [x] GPU 記憶體監控每 30 秒執行
- [x] VRAM > 18GB 時發出警報
- [x] RAG 回覆包含來源引用
- [x] 每日凌晨 2 點自動重啟

## 待完成項目

- Phase 1 完成後的端到端測試（Plan 04）
- 實際部署測試（需要 Qwen 模型和文件）

## 後續階段

本計劃完成後進入：
- Plan 04: 端到端整合測試與診所員工文件

---
*Last updated: 2026-05-06 After Plan 03 execution*