---
title: Phase 4 - Inference Engine Fix (Vulkan Segfault Resolution)
date: 2026-05-11
status: in_progress
---

# Vulkan Segfault Resolution — Comprehensive Fix Plan

## Problem Statement

**Symptom**: Running `llama-server` with either Gemma-4 or Qwen 3.6 models crashes immediately at tensor loading with:
```
程式記憶體區段錯誤 (核心已傾印) [Segmentation Fault - Core Dumped]
```

**Root Cause**: Homebrew's llama-server (v9100) has **Vulkan backend loaded but NO CUDA backend**. Vulkan is unstable on this system; CUDA is the stable path for RTX 2080Ti.

**Environment**:
- System: Linux x86_64 (Ubuntu 24.04)
- GPU: NVIDIA RTX 2080Ti (22.5GB VRAM, Compute Capability 7.5)
- CUDA: 13.0 installed, nvcc available at `/usr/local/cuda/bin/nvcc`
- Current llama-server: Homebrew v9100 (Vulkan only)

---

## Solution: Rebuild with CUDA Support

### Step 1: Clean CUDA Build (IN PROGRESS)
Build location: `/tmp/llama.cpp/build/`
Build command:
```bash
cd /tmp/llama.cpp
mkdir -p build && cd build
cmake .. -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release --target llama-server -j$(nproc)
```

**Status**: Compiling now (target: ~30-45 minutes)

### Step 2: Verify Binary (PENDING)
Once built, verify CUDA backend is loaded:
```bash
/tmp/llama.cpp/build/bin/llama-server --version
# Should show: "loaded CUDA backend"
```

### Step 3: Test with Qwen 3.6 (PENDING)
```bash
export GGML_CUDA=1
/tmp/llama.cpp/build/bin/llama-server \
  --model /home/hsu/DrtoolboxLocalServer/models/Qwen3.6-35B-A3B.Q3_K_M.gguf \
  --port 8081 \
  --gpu-layers 50 \
  --n-batch 256 \
  --verbose
```

Expected: Model loads, prints layer count, waits for requests (no segfault).

### Step 4: Integration Test (PENDING)
```bash
cd /home/hsu/DrtoolboxLocalServer
uv run python scripts/hermes_cli.py chat --query "診所今天有多少病患?"
```

Expected: HermesAgent connects to llama-server, executes intent classification, and returns response.

---

## Rollback Plan

If CUDA build fails:
1. **Fallback 1**: Use CPU inference (slow but stable) — Set `n_gpu_layers: 0` in config
2. **Fallback 2**: Try different llama.cpp branch targeting Compute 7.5 more aggressively
3. **Fallback 3**: Pre-quantize model to Q2_K (smaller, slower but more stable)

---

## Files Modified

- `/tmp/llama.cpp/` — Fresh clone + CUDA build
- `/home/hsu/DrtoolboxLocalServer/config/llama_config.json` — Will be updated to use new binary path
- `.planning/.continue-here.md` — Updated with new checkpoint

---

## Success Criteria

✓ llama-server binary with CUDA backend built successfully
✓ Model loads without segfault
✓ HTTP server listens on port 8081
✓ Hermes CLI chat returns response within 5 seconds

---

## Timeline

- **Build**: ~30-45 min (in progress)
- **Verification**: ~5 min
- **Integration test**: ~2 min
- **Total**: ~1 hour from now

---

## Next Action

Monitor build completion, then verify binary with:
```bash
ls -lh /tmp/llama.cpp/build/bin/llama-server && echo "✓ Ready to test"
```
