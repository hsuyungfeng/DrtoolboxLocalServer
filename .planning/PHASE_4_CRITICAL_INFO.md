# Phase 4 Critical Information

## 🎯 Mission
Deploy Hermes Agent with local LLM (llama.cpp) running on RTX 2080 Ti.
**No cloud dependencies — fully local inference.**

---

## 📊 Current Status

```
Build Progress: 16% → ETA 22:15-22:30
Build Output: /tmp/claude-1000/-home-hsu-DrtoolboxLocalServer/2713240e-f8c0-4459-8222-56373339303b/tasks/bpc6fepr7.output
Monitor: Active (build completion will trigger notification)
```

---

## ⚡ Key Paths & Commands

### Build
```bash
# Monitor build progress
tail -20 /tmp/claude-1000/-home-hsu-DrtoolboxLocalServer/2713240e-f8c0-4459-8222-56373339303b/tasks/bpc6fepr7.output

# When build completes, binary will be here:
/tmp/llama.cpp/build/bin/llama-server
```

### Server (Terminal 1, after build)
```bash
cd /home/hsu/DrtoolboxLocalServer
bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081
# Wait for: "✅ llama-server running on http://127.0.0.1:8081"
```

### Verification (Terminal 2, after server running)
```bash
cd /home/hsu/DrtoolboxLocalServer
source .venv/bin/activate

# Run all checks
bash scripts/verify_phase4.sh

# Health check
python scripts/hermes_cli.py health

# Test chat
python scripts/hermes_cli.py chat --query "診所現在有多少病患?"
```

---

## 🔑 Success Indicators

### Build Success
```
✅ Build complete!
Binary location: /tmp/llama.cpp/build/bin/llama-server
-rwxr-xr-x 1 root root 9.1M May 11 22:15 /tmp/llama.cpp/build/bin/llama-server
```

### Server Success
```
✅ llama-server running on http://127.0.0.1:8081
```

### Hermes Success
```
✓ Hermes Agent initialized
✓ Intent router ready
✓ RAG engine ready
✓ HIS connection ready
✓ Local LLM: http://127.0.0.1:8081 (Ready)
```

---

## 🚨 Critical Resources

| Resource | Location | Size | Status |
|----------|----------|------|--------|
| llama.cpp source | /tmp/llama.cpp/ | ~500MB | ✅ Cloned |
| Build output | /tmp/llama.cpp/build/ | ~2GB | 🔨 In progress |
| Qwen 3.6 model | models/Qwen3.6-35B-A3B.Q3_K_M.gguf | 16GB | ✅ Ready |
| Gemma-4 model | models/gemma-4-31b-jang-crack-Q3_K_M.gguf | 15GB | ✅ Ready |
| HIS Database | data/local_db/clinic.db | ~50MB | ✅ Ready |
| RAG Vector DB | data/rag/chroma/ | ~200MB | ✅ Ready |
| GPU | RTX 2080 Ti | 22GB VRAM | ✅ Ready |

---

## 📈 Timeline

```
21:30: Build starts
  │
  ├─→ 21:35: Clone source ✅
  ├─→ 21:40: Configure CMake ✅
  ├─→ 21:45: Begin compilation ✅
  │
  ├─→ 21:50: 5% (CPU backends)
  ├─→ 22:00: 10% (CUDA kernels starting)
  ├─→ 22:10: 25% (CUDA kernels mid-way)
  ├─→ 22:20: 50% (Linking)
  │
  └─→ 22:15-22:30: BUILD COMPLETE ✅
      └─→ 22:30-23:00: Start server + load model (60-120s)
          └─→ 23:00-23:15: Verification tests
              └─→ 23:15: PHASE 4 COMPLETE ✅
```

---

## 🧠 What Each Component Does

### llama.cpp
Optimized inference engine for GGUF quantized models.
- Compiled with CUDA for RTX 2080 Ti
- Serves /v1/chat/completions endpoint
- Handles 4096 token context
- ~100 tokens/second throughput

### Hermes Agent
Orchestrator that:
1. Classifies user intent (medical/operational)
2. Retrieves context from HIS (patient data) + RAG (medical docs)
3. Constructs prompt
4. Calls llama.cpp locally
5. Returns response + logs for pattern learning

### Pattern Learner
Tracks user queries to identify:
- Repeating patterns
- High-value queries
- Auto-skill candidates
- Usage trends

### HIS Connection
SQLite interface to clinic.db:
- Patient counts
- Doctor information
- Department listings
- Appointment data

### RAG Engine
Chroma vector DB + embeddings:
- Medical knowledge docs
- Clinical procedures
- Clinic protocols
- Best practices

---

## 🎓 Expected Behaviors

### Chat Query
```
User: "診所現在有多少病患?"

Hermes: 
  1. Intent: OPERATIONAL (patient count)
  2. HIS: SELECT COUNT(*) FROM patients → 52
  3. LLM: "根據HIS資料庫，目前有52位掛號患者..."
  Latency: ~3 seconds
```

### Medical Query
```
User: "患者應該掛號多久前到診所?"

Hermes:
  1. Intent: MEDICAL + OPERATIONAL
  2. RAG: Retrieve clinic procedures doc
  3. HIS: Get clinic hours
  4. LLM: "根據診所規定，患者應在約診前10-15分鐘到診所..."
  Latency: ~4 seconds
```

### Mixed Query
```
User: "今天心臟科有哪些醫生?"

Hermes:
  1. Intent: BOTH (medical specialty + doctor info)
  2. HIS: SELECT * FROM doctors WHERE dept='cardiology'
  3. RAG: Cardiology specialists info
  4. LLM: Combines doctor list + specialty details
  Latency: ~5 seconds
```

---

## 🔍 How to Monitor

### Watch Build
```bash
# In a terminal
watch -n 10 'tail -20 /tmp/claude-1000/...tasks/bpc6fepr7.output'
```

### Watch Server Startup (Terminal 1)
```bash
# Will show model loading progress
bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081
```

### Watch Hermes (Terminal 2)
```bash
# Interactive mode shows each query + response
python scripts/hermes_cli.py chat
```

---

## 🛑 Abort Conditions

Stop and troubleshoot if:
1. Build takes >90 minutes (check for compilation errors)
2. Server load takes >180 seconds (model corruption?)
3. Chat response timeout >10 seconds (GPU issue?)
4. Health check shows any "Failed" (config error)
5. Database query returns no results (schema issue?)

---

## ✅ Phase 4 Complete = All True

```
[ ] Build succeeded (binary exists)
[ ] Server running (port 8081 responsive)
[ ] Model loaded (<120s)
[ ] Health check passes (all components Ready)
[ ] HIS query works (patient count returned)
[ ] RAG works (medical docs retrieved)
[ ] Chat responsive (<5s latency)
[ ] No cloud fallback (logs show local LLM)
[ ] Pattern learning active (candidates identified)
[ ] No errors in logs (clean execution)
```

---

## 📞 Emergency Contacts

| Issue | Quick Fix |
|-------|-----------|
| Build stuck >60min | Check `/tmp` free space: `df -h /tmp` |
| Server won't start | Check binary: `ls -lh /tmp/llama.cpp/build/bin/llama-server` |
| Model timeout | Normal for Qwen; wait up to 300s |
| Chat no response | Check server in Terminal 1 |
| Database error | Test: `sqlite3 data/local_db/clinic.db ".tables"` |
| CUDA error | Check GPU: `nvidia-smi` |

---

## 📝 Logs to Check

- Build log: `/tmp/build_log.txt`
- Build task: `/tmp/claude-1000/.../tasks/bpc6fepr7.output`
- Server output: Terminal 1 (llama-server)
- Hermes output: Terminal 2 (hermes_cli.py)
- Database: `sqlite3 data/local_db/clinic.db`

---

## 🎯 Success Condition

**Phase 4 is complete when:**

User asks Hermes a medical question → Gets accurate response from local LLM in <5 seconds, using context from HIS + RAG, with no cloud calls.

**Example**:
```
Query: "診所現在有多少病患?"
Response: (from local Qwen/Gemma, <5s, no cloud)
"根據HIS資料庫，目前有52位掛號患者..."
```

---

*Build in progress. Build monitor active. Will notify at completion.*

**Build ETA**: 22:15-22:30
**Full Phase 4 ETA**: 23:15
