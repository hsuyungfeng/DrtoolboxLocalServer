#!/bin/bash
# Run llama.cpp server with Qwen 3.6 model

set -e

LLAMA_BIN="/home/linuxbrew/.linuxbrew/bin/llama-server"
MODEL_PATH="${1:-/home/hsu/models/qwen-3.6-7b-it.gguf}"
PORT="${2:-8080}"

echo "🚀 Starting llama-server (via python)"
echo "Model: $MODEL_PATH"
echo "Port: $PORT"
echo ""

# Activate virtual environment
source /home/hsu/DrtoolboxLocalServer/.venv/bin/activate

# Check if model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found at $MODEL_PATH"
    ls -lh /home/hsu/models/*.gguf 2>/dev/null || echo "  No models found"
    exit 1
fi

echo "⏳ Loading model (this may take 60-120 seconds)..."
echo ""

# Run llama_cpp.server
export CUDA_VISIBLE_DEVICES=0
python -m llama_cpp.server \
    --model "$MODEL_PATH" \
    --port "$PORT" \
    --n_gpu_layers 35 \
    --n_ctx 32768

echo ""
echo "✅ llama-server running on http://127.0.0.1:$PORT"
