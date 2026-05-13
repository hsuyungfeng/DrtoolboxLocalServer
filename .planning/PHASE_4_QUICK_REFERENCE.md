# Phase 4 Quick Reference Card

## 🎯 Goal
Deploy Hermes Agent with local LLM (llama.cpp) — no cloud dependencies.

---

## 📋 Current Status

**Build**: In Progress (12% complete, ~45-50 min remaining)
- CUDA kernels compiling
- RTX 2080 Ti detected ✓
- Models ready (Qwen 3.6, Gemma-4) ✓

---

## ⏱️ Estimated Timeline

```
Now (May 11, ~21:30):
  ├─→ Build completes: ~22:15-22:30 (45-50 min)
  ├─→ Start server: 2-3 min
  └─→ Verify + test: 15 min
      Total: ~1 hour
```

---

## 🚀 What to Do When Build Completes

### Terminal 1: Start Server
```bash
cd /home/hsu/DrtoolboxLocalServer
bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081
# Wait for: "✅ llama-server running on http://127.0.0.1:8081"
```

### Terminal 2: Verify & Test
```bash
cd /home/hsu/DrtoolboxLocalServer
source .venv/bin/activate

# 1. Verify prerequisites
bash scripts/verify_phase4.sh

# 2. Health check
python scripts/hermes_cli.py health

# 3. Test chat
python scripts/hermes_cli.py chat --query "診所現在有多少病患?"

# 4. Interactive
python scripts/hermes_cli.py chat

# 5. Discover skills
python scripts/hermes_cli.py discover
```

---

## ✅ Success Indicators

- [x] llama-server binary built
- [x] GGUF models ready
- [x] Python env configured
- ⏳ Build completes without errors
- ⏳ Server loads model in <120s
- ⏳ Hermes responds in <5s
- ⏳ HIS query returns patient count
- ⏳ RAG retrieves medical docs

---

## 🔧 If Something Fails

| Error | Quick Fix |
|-------|-----------|
| "Connection refused" | Check llama-server is running in Terminal 1 |
| "CUDA out of memory" | Use gemma model (smaller) or reduce gpu-layers |
| "Model timeout >180s" | Normal for first load; wait up to 300s |
| "HIS connection error" | Check `sqlite3 data/local_db/clinic.db ".tables"` |
| "Python import error" | Run `pip install -r requirements.txt` in venv |

---

## 📞 Contact Points

- Build logs: `/tmp/build_log.txt`
- Hermes logs: Check terminal running hermes_cli.py
- llama-server: Check Terminal 1 for errors
- Database: `sqlite3 data/local_db/clinic.db`

---

## 🎓 What Phase 4 Proves

✅ **Local-only inference works** — no cloud needed for basic queries
✅ **RAG integration** — medical knowledge from documents
✅ **HIS integration** — patient data from clinic database
✅ **Pattern learning** — system identifies repeating queries
✅ **Multi-modal context** — combines HIS + RAG + LLM

---

## 📊 Phase 4 → Phase 5 Roadmap

**Phase 4 (Now)**: Local inference, pattern learning
**Phase 5 (Next)**: Cloud sync, analytics, production deployment

---

*Build ETA: ~22:15-22:30. I'll monitor and notify when complete.*
