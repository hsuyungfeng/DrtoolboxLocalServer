#!/bin/bash
# Run llama.cpp server with Qwen 3.6 model

set -e

LLAMA_BIN="/home/linuxbrew/.linuxbrew/bin/llama-server"
MODEL_PATH="${1:-/home/hsu/llama.cpp/models/Ornith-1.0-9B-UD-Q6_K_XL.gguf}"
PORT="${2:-8080}"

echo "🚀 Starting llama-server"
echo "Model: $MODEL_PATH"
echo "Port: $PORT"
echo ""

# Activate virtual environment
source /home/hsu/Desktop/DrtoolboxLocalServer/.venv/bin/activate || true

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found at $MODEL_PATH"
    ls -lh /home/hsu/models/*.gguf 2>/dev/null || echo "  No models found"
    exit 1
fi

echo "⏳ Loading model (this may take 60-120 seconds)..."
echo ""

# Export both GPUs
export CUDA_VISIBLE_DEVICES=0,1

# Run llama-server with tensor split
# Assuming: GPU 0 is RTX 3060, GPU 1 is GTX 1060 (adjust indices if reversed in nvidia-smi)
# -ts 1,0 : Puts 100% of compute layers on GPU 0 (3060) and 0% on GPU 1 (1060)
# -mg 1   : Forces the KV Cache (Context) to be allocated on GPU 1 (1060)
$LLAMA_BIN \
    -m "$MODEL_PATH" \
    --port "$PORT" \
    -ngl 99 \
    -c 32768 \
    -ts 1,0 \
    -mg 1

echo ""
echo "✅ llama-server running on http://127.0.0.1:$PORT"
