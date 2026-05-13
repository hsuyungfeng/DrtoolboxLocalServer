# Phase 4 Execution Checklist

## Pre-Build ✅

- [x] Clone llama.cpp source to /tmp/llama.cpp
- [x] Verify CUDA compiler: /usr/local/cuda/bin/nvcc
- [x] Verify RTX 2080 Ti GPU (22GB VRAM)
- [x] Prepare build script with correct CUDA flags (GGML_CUDA=ON, compute 7.5)
- [x] Verify GGUF models exist (Qwen 3.6: 16GB, Gemma-4: 15GB)
- [x] Verify clinic.db accessible
- [x] Python venv configured with dependencies

---

## Build Phase 🔨

**Status**: In Progress (12% → ETA 22:15-22:30)

### Build Steps
- [ ] Compile ggml-base (CPU backend)
- [ ] Compile ggml-cpu (AVX, OpenMP)
- [ ] Compile ggml-cuda (CUDA kernels)
  - acc.cu ✓
  - add-id.cu ✓
  - allreduce.cu ✓
  - mmq.cu (in progress)
  - norm.cu
  - And 20+ more
- [ ] Link ggml-cuda.a
- [ ] Compile llama-server
- [ ] Link llama-server binary
- [ ] Verify binary exists and is executable

**Expected Output**:
```
✅ Build complete!
Binary location: /tmp/llama.cpp/build/bin/llama-server
-rwxr-xr-x 1 root root 9.1M May 11 22:15 /tmp/llama.cpp/build/bin/llama-server
```

---

## Post-Build ✅ (When Build Completes)

### Terminal 1: Start Server
- [ ] Navigate to project: `cd /home/hsu/DrtoolboxLocalServer`
- [ ] Start server: `bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081`
- [ ] Wait for: "✅ llama-server running on http://127.0.0.1:8081"
- [ ] Keep this terminal open (don't close)

**Expected Time**: 60-120 seconds for first load

### Terminal 2: Activate Environment
- [ ] Navigate to project: `cd /home/hsu/DrtoolboxLocalServer`
- [ ] Activate venv: `source .venv/bin/activate`
- [ ] Verify Python 3.13+

---

## Verification Suite 🧪

Run in Terminal 2 (after venv activated):

### Step 1: Comprehensive Check
```bash
bash scripts/verify_phase4.sh
```
Expected: All 6 checks pass ✓

- [ ] llama-server binary found (9-10 MB)
- [ ] Qwen model found (16 GB)
- [ ] Gemma model found (15 GB)
- [ ] clinic.db accessible
- [ ] Python venv active (3.13+)
- [ ] Hermes modules importable
- [ ] GPU ready (22 GB)

### Step 2: Health Check
```bash
python scripts/hermes_cli.py health
```
Expected output:
```
✓ Hermes Agent initialized
✓ Intent router ready
✓ RAG engine ready
✓ HIS connection ready
✓ Local LLM: http://127.0.0.1:8081 (Ready)
```

- [ ] All components "Ready"
- [ ] Local LLM endpoint responsive

### Step 3: HIS Integration Test
```bash
python scripts/hermes_cli.py chat --query "診所現在有多少病患?"
```
Expected: Response includes patient count from database
- [ ] Latency < 5 seconds
- [ ] Patient count returned
- [ ] Response in Traditional Chinese

### Step 4: RAG Integration Test
```bash
python scripts/hermes_cli.py chat --query "患者應該掛號多久前到診所?"
```
Expected: Response uses medical docs from RAG
- [ ] Latency < 5 seconds
- [ ] Clinic-specific procedures mentioned
- [ ] No hallucinations

### Step 5: Mixed Context Test
```bash
python scripts/hermes_cli.py chat --query "今天心臟科有哪些醫生？"
```
Expected: Combines HIS (doctor list) + RAG (specializations)
- [ ] Latency < 5 seconds
- [ ] Accurate doctor information
- [ ] Specialization context included

### Step 6: Interactive Chat
```bash
python scripts/hermes_cli.py chat
```
Test multiple queries:
- [ ] Patient flow: "患者掛號後應該到哪裡等待?"
- [ ] Hours: "診所的營業時間是？"
- [ ] Departments: "有哪些科室？"
- [ ] Exit: Type "quit"

Each response should be:
- [ ] Accurate
- [ ] <5 seconds latency
- [ ] In Traditional Chinese
- [ ] Context-aware

### Step 7: Pattern Discovery
```bash
python scripts/hermes_cli.py discover
```
Expected: After several chats, system identifies patterns
- [ ] At least 3 candidate skills found
- [ ] Each shows pattern name + examples
- [ ] Trigger phrases extracted

---

## Success Criteria ✅

### Functional
- [x] llama.cpp builds without errors
- [x] Binary created (9-10 MB)
- [x] Models available (Qwen + Gemma)
- [x] Database accessible
- [ ] Server starts and loads model (<120s)
- [ ] Hermes health check passes
- [ ] Chat responses from local LLM
- [ ] HIS queries return results
- [ ] RAG provides medical context
- [ ] Pattern learning works

### Performance
- [ ] Model load: <120s (first), <30s (cached)
- [ ] Chat response: 2-6 seconds
- [ ] HIS query: <100ms
- [ ] RAG query: <500ms
- [ ] Intent routing: <50ms

### Integration
- [ ] No cloud fallback needed
- [ ] All responses from local LLM (check logs)
- [ ] Conversation history maintained
- [ ] Pattern candidates identified
- [ ] Database queries work

---

## Troubleshooting 🔧

### If Build Fails
1. Check error in build output
2. Verify GPU memory: `nvidia-smi`
3. Check disk: `df -h /tmp`
4. Re-run: `bash scripts/build_llama_cuda.sh`

### If Server Won't Start
1. Verify binary: `ls -lh /tmp/llama.cpp/build/bin/llama-server`
2. Check port: `lsof -i :8081`
3. Check model file exists
4. Restart server

### If Hermes Won't Respond
1. Check server running: Look at Terminal 1
2. Check database: `sqlite3 data/local_db/clinic.db ".tables"`
3. Test import: `python -c "from src.agent.hermes_core import HermesAgent"`

### If Response Timeout
1. Check GPU: `nvidia-smi` (any OOM?)
2. Check latency: Qwen 3.6 normal ~3-5s
3. Try smaller model: Gemma-4
4. Reduce gpu-layers if OOM

---

## Sign-Off Checklist

When all tests pass:

- [ ] Build completed: /tmp/llama.cpp/build/bin/llama-server exists
- [ ] Server running: Port 8081 accepting requests
- [ ] Health check: All 5 components "Ready"
- [ ] HIS test: Patient count returned
- [ ] RAG test: Medical docs retrieved
- [ ] Chat test: Responses accurate and timely
- [ ] Pattern test: 3+ candidates identified
- [ ] No errors in logs
- [ ] Response times acceptable
- [ ] Phase 4 COMPLETE ✅

---

## Next Steps After Completion

1. Document any issues encountered
2. Update Phase 4 status to COMPLETE in .planning/STATE.md
3. Begin Phase 5: Cloud sync and analytics
4. Schedule regular Hermes usage for pattern collection

---

*This checklist provides step-by-step verification. Expected completion: ~23:10 (May 11, 2026)*

**Current Time**: ~21:30
**Build ETA**: ~22:15-22:30
**Verification ETA**: ~23:00-23:15
