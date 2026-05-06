---
phase: 01-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/server.py
  - src/rag/ingest.py
  - src/api/app.py
  - requirements.txt
  - config/llama_config.json
  - data/models/Qwen3-8B-Q8_0.gguf
autonomous: true
requirements:
  - LLM-01
  - RAG-01

must_haves:
  truths:
    - "llama.cpp runs on 2080Ti GPU without OOM"
    - "Qwen 3.6 model loads within 22GB VRAM"
    - "Medical documents can be ingested and indexed"
    - "Flask API server responds to health checks"
  artifacts:
    - path: "src/llm/server.py"
      provides: "llama.cpp server with dynamic batching"
      min_lines: 100
    - path: "src/rag/ingest.py"
      provides: "Document ingestion pipeline for PDF/Word/text"
      min_lines: 80
    - path: "src/api/app.py"
      provides: "Flask API with health and inference endpoints"
      min_lines: 60
    - path: "requirements.txt"
      provides: "Python dependencies for LLM and RAG"
    - path: "config/llama_config.json"
      provides: "llama.cpp configuration for Qwen 3.6"
  key_links:
    - from: "src/api/app.py"
      to: "src/llm/server.py"
      via: "import and function call"
      pattern: "from.*llm.*import"
    - from: "src/api/app.py"
      to: "src/rag/ingest.py"
      via: "import and function call"
      pattern: "from.*rag.*import"
---

<objective>
建立本地 LLM 推理與 RAG 基礎設施。包含 llama.cpp 伺服器、Qwen 3.6 模型載入、文件攝取管道、Flask API 骨架。
</objective>

<execution_context>
@/home/hsu/.config/opencode/get-shit-done/workflows/execute-plan.md
@/home/hsu/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation/01-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: 安裝與設定 llama.cpp 伺服器</name>
  <files>src/llm/server.py, config/llama_config.json, requirements.txt</files>
  <action>
    1. 建立 `src/llm/` 目錄結構
    2. 在 requirements.txt 新增依賴: llama-cpp-python, pynvml, flask
    3. 建立 `config/llama_config.json`:
       - model_path: "data/models/Qwen3-8B-Q8_0.gguf"
       - n_ctx: 2048
       - n_gpu_layers: 99 (all layers to GPU)
       - verbose: true
       - use_mmap: true
       - use_mlock: false
    4. 建立 `src/llm/server.py`:
       - LlamaCppServer class with __init__, load_model, generate, streaming_generate
       - Dynamic batching logic (batch_size 1-4 based on queue depth)
       - Memory monitoring integration (pynvml)
       - Health check method
    5. 參考決策 D-03: 動態批處理基於佇列深度
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -c "from src.llm.server import LlamaCppServer; print('LlamaCppServer import OK')"</automated>
  </verify>
  <done>
    - LlamaCppServer 類別可導入
    - config/llama_config.json 存在且格式正確
    - requirements.txt 包含 llama-cpp-python, pynvml, flask
  </done>
</task>

<task type="auto">
  <name>Task 2: 建立文件攝取管道</name>
  <files>src/rag/ingest.py, config/ingest_config.json</files>
  <action>
    1. 建立 `src/rag/` 目錄結構
    2. 新增依賴: chromadb, PyPDF2, python-docx, tiktoken
    3. 建立 `config/ingest_config.json`:
       - chunk_size: 512
       - chunk_overlap: 50
       - embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
       - chroma_persist_directory: "data/rag/chroma"
    4. 建立 `src/rag/ingest.py`:
       - DocumentIngestor class
       - Supported formats: PDF, Word (.docx), Text (.txt)
       - Chunking with tiktoken token count
       - ChromaDB integration (reuse existing instance)
       - Citation tracking: filename, section, page, timestamp
    5. 參考決策 D-05, D-06, D-07: 小 chunk + Chroma + 函式庫解析
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -c "from src.rag.ingest import DocumentIngestor; print('DocumentIngestor import OK')"</automated>
  </verify>
  <done>
    - DocumentIngestor 類別可導入
    - config/ingest_config.json 存在
    - 支援 PDF, Word, Text 格式
    - 使用現有 Chroma 執行個體 (data/rag/chroma/)
  </done>
</task>

<task type="auto">
  <name>Task 3: 建立 Flask API 骨架</name>
  <files>src/api/app.py, src/api/routes/__init__.py, src/api/routes/inference.py, src/api/routes/rag.py</files>
  <action>
    1. 建立 `src/api/` 目錄結構
    2. 建立 `src/api/app.py`:
       - Flask app with CORS
       - Health check endpoint: GET /health
       - Ready check: GET /ready (llama.cpp loaded + Chroma ready)
    3. 建立 `src/api/routes/inference.py`:
       - POST /api/v1/generate (非串流)
       - POST /api/v1/generate/stream (串流) — 參考決策 D-02
       - Request: {prompt, max_tokens, temperature}
       - Response: {text, tokens_used, inference_ms}
    4. 建立 `src/api/routes/rag.py`:
       - POST /api/v1/rag/query
       - GET /api/v1/rag/search
       - POST /api/v1/rag/ingest (file upload)
    5. 參考決策 D-08: Flask (同步)
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && FLASK_APP=src.api.app python -c "from src.api.app import app; print('Flask app import OK')"</automated>
  </verify>
  <done>
    - Flask app 可導入
    - /health 端點存在
    - /ready 端點存在
    - inference 和 rag 路由模組存在
  </done>
</task>

</tasks>

<verification>
- [ ] 所有 Python 模組可正確導入
- [ ] requirements.txt 包含必要依賴
- [ ] 配置文件格式正確且可讀取
</verification>

<success_criteria>
1. llama.cpp 伺服器類別可實例化
2. 文件攝取類別可處理 PDF/Word/Text
3. Flask API 骨架對 /health 正確回應 200
</success_criteria>

<output>
完成後建立 `.planning/phases/01-foundation/01-01-SUMMARY.md`
</output>

---
phase: 01-foundation
plan: 02
type: execute
wave: 2
depends_on:
  - 01-01
files_modified:
  - data/models/Qwen3-8B-Q8_0.gguf
  - src/llm/server.py
  - src/rag/search.py
  - src/api/routes/inference.py
  - src/api/routes/rag.py
autonomous: true
requirements:
  - LLM-02
  - LLM-03
  - RAG-02

must_haves:
  truths:
    - "Qwen 3.6 模型可在 22GB VRAM 內載入"
    - "推論延遲 <400ms (目標 <200ms)"
    - "語意搜尋在 Chroma 上運作"
    - "串流輸出正常工作"
  artifacts:
    - path: "data/models/Qwen3-8B-Q8_0.gguf"
      provides: "Q8_0 量化模型檔案"
    - path: "src/llm/server.py"
      provides: "模型載入與推論方法"
    - path: "src/rag/search.py"
      provides: "語意搜尋介面"
    - path: "src/api/routes/inference.py"
      provides: "串流推論端點"
  key_links:
    - from: "src/llm/server.py"
      to: "data/models/Qwen3-8B-Q8_0.gguf"
      via: "Llama 模型載入"
      pattern: "model_path.*Qwen"
    - from: "src/api/routes/inference.py"
      to: "src/llm/server.py"
      via: "streaming_generate"
      pattern: "streaming_generate"
---

<objective>
載入 Qwen 3.6 模型、測試推論效能、實作語意搜尋。包含模型下載、載入測試、串流輸出、Chroma 搜尋。
</objective>

<execution_context>
@/home/hsu/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-foundation/01-CONTEXT.md
@.planning/phases/01-foundation/01-01-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 4: 下載與設定 Qwen 模型</name>
  <files>data/models/Qwen3-8B-Q8_0.gguf</files>
  <action>
    1. 建立 `data/models/` 目錄 (如不存在)
    2. 下載 Qwen 3.6 Q8_0 量化模型:
       - Source: HuggingFace (Qwen/Qwen2.5-8B-Instruct-GGUF)
       - File: Qwen2.5-8B-Instruct-Q8_0.gguf
       - Size: ~10GB (Q8_0 quantization)
    3. 驗證檔案完整性 (MD5/SHA256 checksum)
    4. 更新 config/llama_config.json model_path
    5. 參考決策 D-01: Q8_0 量化, ~10GB VRAM, ~250-300ms
  </action>
  <verify>
    <automated>ls -la /home/hsu/DrtoolboxLocalServer/data/models/Qwen3-8B-Q8_0.gguf</automated>
  </verify>
  <done>
    - 模型檔案存在於 data/models/
    - 檔案大小約 8-10GB
  </done>
</task>

<task type="auto">
  <name>Task 5: 實作模型推論與串流輸出</name>
  <files>src/llm/server.py</files>
  <action>
    1. 擴充 LlamaCppServer:
       - load_model(): 使用 llama-cpp-python 載入模型
       - generate(): 標準產生
       - streaming_generate(): yield tokens with timing
    2. 實現動態批處理:
       - Queue depth 監控
       - batch_size = min(4, max(1, queue_depth // 2))
       - 參考決策 D-03
    3. 添加推論計時:
       - 追蹤 tokens生成時間
       - 回傳 inference_ms
    4. 測試延遲:
       - 目標: <400ms (初始測試), <200ms (優化後)
       - 記錄實際延遲到日誌
    5. 參考決策 D-02: 串流輸出
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -c "
from src.llm.server import LlamaCppServer
# Test that methods exist
server = LlamaCppServer()
print('has load_model:', hasattr(server, 'load_model'))
print('has generate:', hasattr(server, 'generate'))
print('has streaming_generate:', hasattr(server, 'streaming_generate'))
"</automated>
  </verify>
  <done>
    - load_model() 可呼叫且不拋出異常
    - generate() 回傳文字
    - streaming_generate() yield tokens
    - 推論延遲記錄到日誌
  </done>
</task>

<task type="auto">
  <name>Task 6: 實作語意搜尋</name>
  <files>src/rag/search.py, src/rag/query.py</files>
  <action>
    1. 建立 `src/rag/search.py`:
       - SemanticSearch class
       - query(chroma_collection, query_text, top_k)
       - 使用現有 Chroma 執行個體 (data/rag/chroma/)
    2. 建立 `src/rag/query.py`:
       - QueryAnswer class
       - retrieve_context(), generate_answer()
       - confidence_score 計算 (相似度 >0.7 = high, >0.4 = medium, else low)
    3. 整合 RAG 端點:
       - /api/v1/rag/search -> SemanticSearch
       - /api/v1/rag/query -> QueryAnswer
    4. 參考決策 D-04: 僅語意搜尋
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -c "
from src.rag.search import SemanticSearch
from src.rag.query import QueryAnswer
print('SemanticSearch import OK')
print('QueryAnswer import OK')
"</automated>
  </verify>
  <done>
    - SemanticSearch 類別可導入
    - QueryAnswer 類別可導入
    - 信心分數計算正確
  </done>
</task>

</tasks>

<verification>
- [ ] 模型檔案存在且大小正確
- [ ] 推論方法可呼叫
- [ ] 搜尋類別可導入
</verification>

<success_criteria>
1. Qwen 模型成功載入 (無 OOM)
2. 推論延遲記錄且 <400ms
3. 語意搜尋回傳結果
</success_criteria>

<output>
完成後建立 `.planning/phases/01-foundation/01-02-SUMMARY.md`
</output>

---
phase: 01-foundation
plan: 03
type: execute
wave: 3
depends_on:
  - 01-02
files_modified:
  - src/llm/server.py
  - src/rag/query.py
  - src/api/routes/rag.py
  - config/memory_config.json
autonomous: true
requirements:
  - LLM-04
  - RAG-03
  - RAG-04

must_haves:
  truths:
    - "GPU 記憶體監控每 30 秒執行"
    - "VRAM > 18GB 時發出警報"
    - "RAG 回覆包含來源引用"
    - "每日凌晨 2 點自動重啟"
  artifacts:
    - path: "src/llm/server.py"
      provides: "GPU 記憶體監控方法"
    - path: "src/rag/query.py"
      provides: "來源引用追蹤"
    - path: "src/api/routes/rag.py"
      provides: "RAG 查詢端點"
    - path: "config/memory_config.json"
      provides: "記憶體監控配置"
  key_links:
    - from: "src/llm/server.py"
      to: "pynvml"
      via: "nvmlDeviceGetMemoryInfo"
      pattern: "pynvml.*memory"
    - from: "src/rag/query.py"
      to: "data/rag/chroma"
      via: "Chroma collection query"
      pattern: "chroma.*query"
---

<objective>
完整 RAG 查詢系統與 GPU 記憶體監控。包含信心分數、來源引用、VRAM 警報、每日重啟。
</objective>

<execution_context>
@/home/hsu/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-foundation/01-CONTEXT.md
@.planning/phases/01-foundation/01-02-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 7: GPU 記憶體監控</name>
  <files>src/llm/server.py, config/memory_config.json</files>
  <action>
    1. 擴充 LlamaCppServer:
       - init_nvml(): 初始化 pynvml
       - get_gpu_memory(): 取得 VRAM 使用量
       - check_memory_threshold(): 检查是否超過閾值
    2. 建立 `config/memory_config.json`:
       - polling_interval_seconds: 30
       - warning_threshold_gb: 18
       - critical_threshold_gb: 20
       - alert_webhook: null (可擴充)
    3. 實現記憶體監控執行緒:
       - 每 30 秒輪詢
       - 超過 18GB 記錄 warning
       - 超過 20GB 記錄 critical 並考慮停止新請求
    4. 實現 stream 停止邏輯:
       - VRAM spike 時立即停止串流
       - 參考決策 D-11
    5. 參考決策 D-10: nvidia-smi + pynvml
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -c "
from src.llm.server import LlamaCppServer
server = LlamaCppServer()
print('has get_gpu_memory:', hasattr(server, 'get_gpu_memory'))
print('has check_memory_threshold:', hasattr(server, 'check_memory_threshold'))
"</automated>
  </verify>
  <done>
    - get_gpu_memory() 可呼叫
    - check_memory_threshold() 回傳布林值
    - 配置檔案存在
  </done>
</task>

<task type="auto">
  <name>Task 8: RAG 信心分數與來源引用</name>
  <files>src/rag/query.py</files>
  <action>
    1. 擴充 QueryAnswer:
       - calculate_confidence(): 基於 Chroma 相似度
       - format_citations(): 格式化來源引用
    2. 來源引用格式:
       - document_name: "filename.pdf"
       - section_heading: "Introduction"
       - page_number: 1
       - chunk_index: 3
       - ingestion_timestamp: "2026-05-06T12:00:00Z"
    3. API 回應格式:
       - answer: "..."
       - confidence: 0.85
       - confidence_level: "high"
       - citations: [{doc, section, page, ...}]
    4. 參考決策 D-09: 完整文件 + 區段追蹤
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -c "
from src.rag.query import QueryAnswer
qa = QueryAnswer()
print('has calculate_confidence:', hasattr(qa, 'calculate_confidence'))
print('has format_citations:', hasattr(qa, 'format_citations'))
"</automated>
  </verify>
  <done>
    - calculate_confidence() 回傳 0-1 分數
    - format_citations() 回傳引用列表
    - 回應包含必要欄位
  </done>
</task>

<task type="auto">
  <name>Task 9: 每日重啟機制</name>
  <files>scripts/daily_restart.sh, cron/crontab.txt</files>
  <action>
    1. 建立 `scripts/daily_restart.sh`:
       - 優雅停止 llama.cpp 伺服器
       - 清除快取 (如有)
       - 重新啟動服務
    2. 建立 `cron/crontab.txt`:
       - 0 2 * * * /home/hsu/DrtoolboxLocalServer/scripts/daily_restart.sh
       - 參考決策 D-12: 凌晨 2 點
    3. 設置 cron job:
       - crontab cron/crontab.txt (需使用者確認)
    4. 記錄重啟日誌到 logs/restart.log
  </action>
  <verify>
    <automated>ls -la /home/hsu/DrtoolboxLocalServer/scripts/daily_restart.sh</automated>
  </verify>
  <done>
    - 腳本存在且可執行
    - cron 排程存在
    - 需使用者設置 crontab
  </done>
</task>

</tasks>

<verification>
- [ ] 記憶體監控方法存在
- [ ] 信心分數計算正確
- [ ] 來源引用格式正確
- [ ] 重啟腳本存在
</verification>

<success_criteria>
1. GPU 記憶體每 30 秒監控
2. RAG 回覆包含信心分數和來源引用
3. 每日重啟腳本存在且可用
</success_criteria>

<output>
完成後建立 `.planning/phases/01-foundation/01-03-SUMMARY.md`
</output>

---
phase: 01-foundation
plan: 04
type: execute
wave: 4
depends_on:
  - 01-03
files_modified: []
autonomous: false
requirements:
  - LLM-01
  - LLM-02
  - LLM-03
  - LLM-04
  - RAG-01
  - RAG-02
  - RAG-03
  - RAG-04

must_haves:
  truths:
    - "端到端 RAG 查詢運作正常"
    - "模型延遲 <200ms"
    - "Relevance > 0.7"
    - "24 小時穩定運作"
  artifacts:
    - path: "docs/clinic_user_guide.md"
      provides: "診所員工使用文件"
    - path: "tests/e2e_rag_test.py"
      provides: "End-to-end RAG 測試"
  key_links:
    - from: "Flask API"
      to: "LLM + Chroma"
      via: "完整請求流程"
---

<objective>
端到端驗證與診所員工文件中繼。所有功能整合測試、使用者文件、工作穩定性驗證。
</objective>

<execution_context>
@/home/hsu/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-foundation/01-CONTEXT.md
@.planning/phases/01-foundation/01-03-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 10: 端到端整合測試</name>
  <files>tests/e2e_rag_test.py</files>
  <action>
    1. 建立 `tests/e2e_rag_test.py`:
       - test_health_check(): /health 回應 200
       - test_model_load(): 模型載入成功
       - test_inference_latency(): <400ms
       - test_rag_query(): 查詢並驗證回覆
       - test_citations(): 驗證引用存在
       - test_streaming(): 驗證串流輸出
    2. 執行測試:
       - 所有測試通過
    3. 記錄效能指標:
       - 模型載入時間
       - 推論延遲
       - RAG 查詢時間
    4. 參考 ROADMAP.md 成功標準
  </action>
  <verify>
    <automated>cd /home/hsu/DrtoolboxLocalServer && python -m pytest tests/e2e_rag_test.py -v --tb=short</automated>
  </verify>
  <done>
    - 所有端到端測試通過
    - 延遲指標記錄
  </done>
</task>

<task type="auto">
  <name>Task 11: 建立診所員工文件</name>
  <files>docs/clinic_user_guide.md</files>
  <action>
    1. 建立 `docs/clinic_user_guide.md`:
       - 系統概述
       - 如何提出 RAG 查詢
       - 解讀信心分數
       - 查看來源引用
       - 故障排除
       - 緊急聯繫資訊
    2. 確保文件:
       - 簡單易懂
       - 包含截圖 (如有)
       - 常見問題解答
    3. 參考交付物: 診所員工文件
  </action>
  <verify>
    <automated>ls -la /home/hsu/DrtoolboxLocalServer/docs/clinic_user_guide.md</automated>
  </verify>
  <done>
    - 使用文件存在
    - 涵蓋基本操作
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Task 12: 人力驗證 - 完整系統運作</name>
  <what-built>Phase 1 完整系���: LLM + RAG + API + 監控</what-built>
  <how-to-verify>
    1. 啟動 Flask 伺服器: `python -m src.api.app`
    2. 測試 health: `curl http://localhost:5000/health`
    3. 測試 RAG 查詢:
       ```bash
       curl -X POST http://localhost:5000/api/v1/rag/query \
         -H "Content-Type: application/json" \
         -d '{"query": "糖尿病的治療方式是什麼？"}'
       ```
    4. 檢查回覆包含:
       - answer 文字
       - confidence 分數 (>0.7 目標)
       - citations 陣列
    5. 驗證引用可點擊/存取來源文件
  </how-to-verify>
  <resume-signal>輸入 "approved" 或描述問題</resume-signal>
</task>

</tasks>

<verification>
- [ ] 端到端測試通過
- [ ] 使用文件存在
- [ ] 人力驗證通過
</verification>

<success_criteria>
1. 系統完整運作: LLM + RAG + API
2. RAG 回覆包含信心分數 >0.7
3. 來源引用完整顯示
4. 人力驗證通過
</success_criteria>

<output>
完成後建立 `.planning/phases/01-foundation/01-04-SUMMARY.md`
</output>