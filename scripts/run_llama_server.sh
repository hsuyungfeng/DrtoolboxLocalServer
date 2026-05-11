#!/bin/bash
# Run llama.cpp server with Gemma4 or Qwen 3.6 model

set -e

LLAMA_BIN="/tmp/llama.cpp/build/bin/llama-server"
MODEL_PATH="${1:-models/Qwen3.6-35B-A3B.Q3_K_M.gguf}"
PORT="${2:-8081}"

echo "🚀 Starting llama-server"
echo "Model: $MODEL_PATH"
echo "Port: $PORT"
echo ""

# Check if binary exists
if [ ! -f "$LLAMA_BIN" ]; then
    echo "❌ llama-server binary not found at $LLAMA_BIN"
    echo "Run: bash scripts/build_llama_cuda.sh"
    exit 1
fi

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found at $MODEL_PATH"
    echo "Available models:"
    ls -lh models/*.gguf 2>/dev/null || echo "  No models found"
    exit 1
fi

echo "⏳ Loading model (this may take 60-120 seconds)..."
echo ""

# Run llama-server
$LLAMA_BIN \
    --model "$MODEL_PATH" \
    --port "$PORT" \
    --gpu-layers 50 \
    -c 4096 \
    -t 4 \
    --verbose 1

echo ""
echo "✅ llama-server running on http://127.0.0.1:$PORT"
