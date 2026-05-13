# Phase 4 Testing Guide

## Quick Start (After Build Completes)

### Terminal 1: Start llama-server
```bash
cd /home/hsu/DrtoolboxLocalServer
bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081
```

Expected output (within 60-120 seconds):
```
🚀 Starting llama-server
Model: models/Qwen3.6-35B-A3B.Q3_K_M.gguf
Port: 8081

⏳ Loading model (this may take 60-120 seconds)...

llm_load_tensors: ggml ctx size = ...
llm_load_tensors: CPU buffer size = ...
llama_new_context_with_model: n_ctx = 4096, n_batch = 512
main: warming up the model with an empty run
main: model loaded successfully

✅ llama-server running on http://127.0.0.1:8081
```

**Keep this terminal open** — it runs the LLM server.

---

### Terminal 2: Run Verification & Tests

#### Step 1: Activate Python environment
```bash
cd /home/hsu/DrtoolboxLocalServer
source .venv/bin/activate
```

#### Step 2: Run verification script
```bash
bash scripts/verify_phase4.sh
```

Expected output:
```
🧪 Phase 4 Verification Suite
================================

[1/6] Checking llama-server binary...
✓ llama-server found (9.1M)

[2/6] Checking GGUF models...
✓ Qwen 3.6 model found (16G)
✓ Gemma-4 model found (15G)

[3/6] Checking HIS database...
✓ clinic.db exists with tables: patients appointments doctors...

[4/6] Checking Python environment...
✓ Virtual environment active (Python 3.13.11)

[5/6] Checking Hermes imports...
✓ Hermes modules loadable

[6/6] Checking GPU...
✓ GPU ready: 22528 MiB (Driver: 580.159.03)

✅ All Phase 4 prerequisites verified!
```

#### Step 3: Health check
```bash
python scripts/hermes_cli.py health
```

Expected output:
```
🏥 Hermes Agent Health Check

✓ Hermes Agent initialized
✓ Intent router ready
✓ RAG engine ready
✓ HIS connection ready
✓ Local LLM: http://127.0.0.1:8081 (Ready)
```

If you see "Local LLM: ... (Ready)" — **Phase 4 is working!**

---

## Test Cases

### Test 1: Patient Query (HIS Integration)
```bash
python scripts/hermes_cli.py chat --query "診所現在有多少病患?"
```

Expected:
- Response should include patient count from clinic.db
- Latency < 5 seconds
- Uses local LLM (no cloud fallback)

Example response:
```
根據HIS資料庫，目前掛號的患者共有{N}位。其中{M}位已經看診...
```

### Test 2: Medical Knowledge (RAG)
```bash
python scripts/hermes_cli.py chat --query "患者應該掛號多久前到診所?"
```

Expected:
- Response uses medical docs from RAG
- Provides clinic-specific procedures
- Latency < 5 seconds

Example response:
```
根據診所規定，建議患者在約診時間前10-15分鐘到診所報到。
這樣有足夠時間完成掛號和基本資料確認...
```

### Test 3: Operational Query (Mixed)
```bash
python scripts/hermes_cli.py chat --query "今天心臟科有哪些醫生？"
```

Expected:
- Response combines HIS (doctor list) + RAG (specializations)
- Accurate and specific
- Latency < 5 seconds

### Test 4: Interactive Chat (Pattern Learning)
```bash
python scripts/hermes_cli.py chat
```

Type medical questions:
```
You: 患者掛號後應該到哪裡等待?
Hermes: 患者掛號後應該在等候區等待叫號。我們的等候區位於...

You: 診所的營業時間是？
Hermes: 診所營業時間是週一至週五 09:00-17:00，週六 09:00-12:00，週日休診。

You: quit
```

### Test 5: Pattern Discovery (Skill Candidates)
```bash
python scripts/hermes_cli.py discover
```

Expected output (after chatting a few times):
```
Found 3 Candidate Skills from conversation patterns:

[1] Pattern: '查詢患者數量' (Seen 2 times)
    Trigger: ["現在有多少病患", "目前患者數"]
    Example: "診所現在有多少病患?"
    
[2] Pattern: '查詢醫生資訊' (Seen 1 times)
    Trigger: ["有哪些醫生", "醫生是誰"]
    Example: "今天心臟科有哪些醫生?"
    
[3] Pattern: '患者流程' (Seen 1 times)
    Trigger: ["應該多久前", "到哪裡"]
    Example: "患者應該掛號多久前到診所?"

Ready to generate auto-skills! Run: hermes_cli.py approve
```

---

## Success Criteria

| Test | Expected Result | Status |
|------|-----------------|--------|
| Build | Binary exists at /tmp/llama.cpp/build/bin/llama-server | ⏳ Pending |
| Model load | <120s, GPU detected | ⏳ Pending |
| Health check | All components "Ready" | ⏳ Pending |
| HIS query | Patient count returned in <5s | ⏳ Pending |
| RAG query | Medical docs retrieved in <5s | ⏳ Pending |
| Pattern learning | 3+ candidate skills discovered | ⏳ Pending |
| No cloud fallback | All responses from local LLM | ⏳ Pending |

---

## Troubleshooting

### "Connection refused @ 127.0.0.1:8081"
**Problem**: llama-server not running or crashed
**Solution**:
```bash
# Check if server is running
lsof -i :8081

# If not running, restart
bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081
```

### "CUDA out of memory"
**Problem**: Model too large for GPU
**Solution**:
```bash
# Edit run_llama_server.sh, change:
--gpu-layers 50
# To:
--gpu-layers 30
```

Or use smaller model:
```bash
bash scripts/run_llama_server.sh models/gemma-4-31b-jang-crack-Q3_K_M.gguf 8081
```

### "Model loading timeout (>180s)"
**Problem**: First load is slow (normal for Qwen 3.6)
**Solution**:
- Wait up to 300s for first load
- Subsequent loads will be cached and faster
- If stuck >300s, check GPU memory with `nvidia-smi`

### "HIS connection error"
**Problem**: clinic.db corrupted or missing
**Solution**:
```bash
# Check database
sqlite3 data/local_db/clinic.db ".tables"

# Should show: patients appointments doctors departments ...

# If empty, reinitialize:
python -c "from src.db.init_db import init_database; init_database()"
```

### "Hermes import failed"
**Problem**: Python path or dependencies missing
**Solution**:
```bash
# Verify venv
source .venv/bin/activate
pip install -r requirements.txt

# Test import
python -c "from src.agent.hermes_core import HermesAgent; print('OK')"
```

---

## Performance Metrics

### Expected Latencies (RTX 2080 Ti)

| Operation | Latency | Notes |
|-----------|---------|-------|
| Model load (first) | 60-120s | VRAM cached |
| Model load (cached) | 10-30s | Subsequent loads |
| Chat response | 2-5s | 512 tokens @ 100 tok/s |
| HIS query | <100ms | SQLite |
| RAG query | <500ms | Chroma DB |
| Intent routing | <50ms | Rule-based |
| **Total end-to-end** | **2-6s** | Dominated by LLM |

### GPU Memory Usage

- Qwen 3.6 (35B): ~16-18 GB
- Gemma-4 (31B): ~14-16 GB
- Remaining: ~4-8 GB for system

---

## What's Next After Verification?

✅ **Phase 4 Complete**:
- Hermes Agent working with local Qwen/Gemma
- Pattern learning tracking clinic queries
- 3+ auto-skill candidates identified

🚀 **Phase 5** (Cloud Sync):
- Deploy to doctor-toolbox.com
- Analytics dashboard
- Skill adoption metrics
- Production hardening

---

## Logs & Debugging

### Check Hermes logs
```bash
tail -f /tmp/hermes.log
```

### Check llama-server logs (in Terminal 1)
Look at the terminal where llama-server is running for any errors.

### Check database
```bash
sqlite3 data/local_db/clinic.db
sqlite> SELECT COUNT(*) FROM patients;
sqlite> .exit
```

### Enable verbose logging
```bash
export DEBUG=1
python scripts/hermes_cli.py chat --query "test"
```

---

*This guide provides step-by-step verification for Phase 4 Local LLM integration. All tests should pass within 30 minutes of build completion.*
