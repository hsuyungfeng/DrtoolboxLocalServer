#!/bin/bash
# GPU Layer Optimization Test for Qwen 3.6-35B on RTX 2080 Ti (22GB VRAM)
# Test increasing layer counts: 20 (baseline) → 25 → 30 → 35
# Each test runs 3 inference requests and monitors VRAM

set -e

LLAMA_BIN="/tmp/llama.cpp/build/bin/llama-server"
MODEL_PATH="${1:-models/Qwen3.6-35B-A3B.Q3_K_M.gguf}"
PORT=8082
TEST_PROMPT="請用繁體中文回答：診所現在有多少病患？"
TIMEOUT=120

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  GPU Layer Optimization Test — Qwen 3.6-35B on RTX 2080 Ti ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Model: $MODEL_PATH"
echo "GPU: RTX 2080 Ti, 22GB VRAM"
echo "Test sequence: 20 (baseline) → 25 → 30 → 35 layers"
echo ""

# Test layers
LAYERS=(20 25 30 35)
RESULTS=()

for gpu_layers in "${LAYERS[@]}"; do
    echo "─────────────────────────────────────────────────────────────"
    echo "Testing: --gpu-layers $gpu_layers"
    echo "─────────────────────────────────────────────────────────────"

    # Kill any existing llama-server on this port
    pkill -f "llama-server.*--port $PORT" 2>/dev/null || true
    sleep 2

    # Start llama-server with test layers
    echo "Starting llama-server (this may take 30-60 seconds)..."
    $LLAMA_BIN \
        --model "$MODEL_PATH" \
        --port "$PORT" \
        --gpu-layers "$gpu_layers" \
        -c 2048 \
        -t 4 \
        --verbose 0 \
        > /tmp/llama_test_$gpu_layers.log 2>&1 &

    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"

    # Wait for server to start
    echo "Waiting for server to initialize..."
    sleep 10

    # Check if server is still running
    if ! ps -p $SERVER_PID > /dev/null; then
        echo -e "${RED}✗ Server crashed during startup${NC}"
        RESULTS+=("$gpu_layers layers: CRASH (see /tmp/llama_test_$gpu_layers.log)")
        continue
    fi

    # Test inference
    echo "Running inference test..."

    TOTAL_TIME=0
    PEAK_VRAM=0
    SUCCESS_COUNT=0

    for i in {1..3}; do
        echo "  Request $i/3..."

        # Capture VRAM before request
        VRAM_BEFORE=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)

        # Make inference request with timeout
        START_TIME=$(date +%s%N)

        if timeout $TIMEOUT curl -s "http://127.0.0.1:$PORT/completion" \
            -H "Content-Type: application/json" \
            -d "{\"prompt\": \"$TEST_PROMPT\", \"n_predict\": 50}" \
            > /tmp/inference_$i.json 2>/dev/null; then

            END_TIME=$(date +%s%N)
            ELAPSED=$(( (END_TIME - START_TIME) / 1000000 ))  # Convert to ms
            TOTAL_TIME=$((TOTAL_TIME + ELAPSED))
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

            # Capture VRAM after request
            sleep 1
            VRAM_AFTER=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)

            if [ "$VRAM_AFTER" -gt "$PEAK_VRAM" ]; then
                PEAK_VRAM=$VRAM_AFTER
            fi

            echo "    ✓ ${ELAPSED}ms (VRAM: ${VRAM_BEFORE}MB → ${VRAM_AFTER}MB)"
        else
            echo "    ✗ Timeout or error"
        fi
    done

    # Cleanup
    kill $SERVER_PID 2>/dev/null || true
    sleep 2

    # Calculate averages
    if [ $SUCCESS_COUNT -gt 0 ]; then
        AVG_TIME=$((TOTAL_TIME / SUCCESS_COUNT))
        STATUS="${GREEN}✓${NC}"
        echo ""
        echo -e "${STATUS} --gpu-layers $gpu_layers"
        echo "  Successful: $SUCCESS_COUNT/3"
        echo "  Avg latency: ${AVG_TIME}ms"
        echo "  Peak VRAM: ${PEAK_VRAM}MB / 22528MB"
        echo ""
        RESULTS+=("$gpu_layers layers: SUCCESS (${AVG_TIME}ms avg, ${PEAK_VRAM}MB peak)")
    else
        echo -e "${RED}✗${NC} --gpu-layers $gpu_layers — all requests failed"
        RESULTS+=("$gpu_layers layers: FAILED (all 3 requests timed out or errored)")
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Test Results Summary                                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

for result in "${RESULTS[@]}"; do
    echo "  $result"
done

echo ""
echo "Recommendation:"
echo "  Test completed. Review VRAM usage and latency above."
echo "  Safe choice: Highest stable layer count with <20GB peak VRAM"
echo "  Update: scripts/run_llama_server.sh with --gpu-layers N"
echo ""
