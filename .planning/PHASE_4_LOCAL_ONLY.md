---
phase: 4-Hermes-Agent
status: local-llm-only
date: 2026-05-11
---

# Phase 4: Hermes Agent + Local LLM (llama.cpp)

## Architecture: Local-Only, No Cloud

```
User Query
    ↓
HermesAgent
    ├─→ Intent Classification (medical/operational)
    ├─→ Context: RAG (medical docs) + HIS (patient data)
    └─→ LLM Inference: Local llama.cpp @ http://127.0.0.1:8081
        ├─→ Model: Gemma4 (31B) or Qwen 3.6 (35B)
        ├─→ GPU: RTX 2080Ti (22GB VRAM)
        └─→ Response + Pattern Learning
```

---

## ✅ Preparation Steps (While GPU Reboots)

### 1. Make build scripts executable
```bash
chmod +x scripts/build_llama_cuda.sh
chmod +x scripts/run_llama_server.sh
```

### 2. Verify models exist
```bash
ls -lh models/*.gguf
# Expected:
# - models/Qwen3.6-35B-A3B.Q3_K_M.gguf (16 GB)
# - models/gemma-4-31b-jang-crack-Q3_K_M.gguf (14.5 GB)
```

### 3. Check llama.cpp source
```bash
ls -la /tmp/llama.cpp/CMakeLists.txt
# Should exist from previous attempt
```

---

## 🏗️ After Reboot: Build llama.cpp (30-60 min)

```bash
# Ensure GPU is free
nvidia-smi

# Build with CUDA
bash scripts/build_llama_cuda.sh

# Expected output at end:
# -rwxr-xr-x 1 root root 9.1M May 11 20:15 /tmp/llama.cpp/build/bin/llama-server
# ✅ Build complete!
```

**What to watch for**:
- CUDA compute capability 7.5 detection (RTX 2080Ti)
- No OOM errors during build
- Binary size ~9-10 MB

**If build fails**:
- Check GPU memory: `nvidia-smi` (should be free)
- Check disk space: `df -h /tmp` (need ~5GB)
- Re-run: `bash scripts/build_llama_cuda.sh`

---

## 🚀 Start llama.cpp Server

### Option 1: Qwen 3.6 (16 GB, more capable)
```bash
bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081
```

### Option 2: Gemma4 (14.5 GB, faster)
```bash
bash scripts/run_llama_server.sh models/gemma-4-31b-jang-crack-Q3_K_M.gguf 8081
```

**Expected output**:
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

**Keep this terminal open** — don't close it while testing Hermes.

---

## ✅ Phase 4 Verification (In another terminal)

### Step 1: Activate venv
```bash
source .venv/bin/activate
```

### Step 2: Check Hermes health
```bash
python scripts/hermes_cli.py health
```

**Expected**:
```
🏥 Hermes Agent Health Check

✓ Hermes Agent initialized
✓ Intent router ready
✓ RAG engine ready
✓ HIS connection ready
✓ Local LLM: http://127.0.0.1:8081 (Ready)
```

### Step 3: Chat with Hermes
```bash
python scripts/hermes_cli.py chat --query "診所現在有多少病患?"
```

**Expected**:
```
📝 Query: 診所現在有多少病患?
⏳ Processing...

💬 Response:
根據HIS資料庫，目前有{N}位掛號病患。今天已看診{M}位...
```

### Step 4: Interactive chat (test pattern learning)
```bash
python scripts/hermes_cli.py chat
```

Type medical questions:
```
You: 患者應該掛號多久前到診所?
Hermes: 一般建議患者在約診時間前10-15分鐘到診所...

You: 診所的心臟科醫生有誰?
Hermes: 根據HIS資料庫，心臟科團隊包括...

You: quit
```

### Step 5: Discover candidate skills
```bash
python scripts/hermes_cli.py discover
```

**Expected**:
```
Found 3 Candidate Skills:
[1] Pattern: '查詢患者數量' (Seen 2 times)
[2] Pattern: '查詢科室醫生' (Seen 1 times)
[3] Pattern: '患者預約流程' (Seen 1 times)
```

---

## 📊 Success Criteria

| Test | Expected | Status |
|------|----------|--------|
| llama.cpp builds | No errors, binary exists | ⏳ Pending |
| Model loads | <120s, CUDA detected | ⏳ Pending |
| Hermes chat | Response <5s | ⏳ Pending |
| Pattern discovery | 3+ candidate skills | ⏳ Pending |
| HIS integration | Patient counts returned | ⏳ Pending |
| RAG context | Medical docs retrieved | ⏳ Pending |

---

## 🧪 Troubleshooting

### "CUDA out of memory"
- Reduce GPU layers: change `--gpu-layers 50` to `--gpu-layers 30`
- Use Gemma4 (smaller) instead of Qwen 3.6

### "Model loading timeout (>180s)"
- Normal for first load with Qwen 3.6 (16GB)
- Subsequent loads faster (cached)
- If stuck >300s, restart llama-server

### "Connection refused @ 127.0.0.1:8081"
- Check llama-server is running: `lsof -i :8081`
- Verify port not in use: `netstat -tlnp | grep 8081`
- Restart: kill process + re-run `run_llama_server.sh`

### "HIS connection error"
- Check clinic.db exists: `ls -la data/local_db/clinic.db`
- Verify schema: `sqlite3 data/local_db/clinic.db ".tables"`
- Check permissions: `file data/local_db/clinic.db`

---

## 📋 What Happens After Phase 4

✅ **Phase 4 Complete**:
- Hermes agent working with local Gemma4/Qwen
- Pattern learning tracking clinic queries
- Auto-skill candidates identified

🚀 **Phase 5**:
- Cloud sync to doctor-toolbox.com
- Analytics dashboard
- Skill adoption metrics
- Production hardening

---

## 🎯 Timeline

```
Now (May 11, ~21:00):
  ├─→ Reboot system (10 min)
  ├─→ Build llama.cpp (30-60 min)
  └─→ Verify Phase 4 (15 min)
      Total: ~1-2 hours

Done:
  ├─→ Phase 4 Hermes Agent ✅
  ├─→ Pattern Learning ✅
  ├─→ Skill Discovery ✅
  └─→ Local LLM Integration ✅
```

---

*Phase 4 ready to execute. All code, scripts, and documentation prepared. Awaiting GPU reboot and llama.cpp build.*
