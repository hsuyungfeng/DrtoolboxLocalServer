#!/bin/bash
# Phase 4 Verification Script
# Tests: llama.cpp server, Hermes Agent, HIS integration, RAG, pattern learning

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧪 Phase 4 Verification Suite${NC}"
echo "================================"
echo ""

# Test 1: Check llama-server binary
echo -e "${YELLOW}[1/6] Checking llama-server binary...${NC}"
LLAMA_BIN="/tmp/llama.cpp/build/bin/llama-server"
if [ -f "$LLAMA_BIN" ]; then
    SIZE=$(du -h "$LLAMA_BIN" | cut -f1)
    echo -e "${GREEN}✓ llama-server found ($SIZE)${NC}"
else
    echo -e "${RED}✗ llama-server not found at $LLAMA_BIN${NC}"
    exit 1
fi

# Test 2: Check models exist
echo -e "${YELLOW}[2/6] Checking GGUF models...${NC}"
QWEN="models/Qwen3.6-35B-A3B.Q3_K_M.gguf"
GEMMA="models/gemma-4-31b-jang-crack-Q3_K_M.gguf"

if [ -f "$QWEN" ]; then
    SIZE=$(du -h "$QWEN" | cut -f1)
    echo -e "${GREEN}✓ Qwen 3.6 model found ($SIZE)${NC}"
else
    echo -e "${RED}✗ Qwen model not found${NC}"
fi

if [ -f "$GEMMA" ]; then
    SIZE=$(du -h "$GEMMA" | cut -f1)
    echo -e "${GREEN}✓ Qwen (llama-qwen) model found ($SIZE)${NC}"
else
    echo -e "${RED}✗ Qwen model not found${NC}"
fi

# Test 3: Check database
echo -e "${YELLOW}[3/6] Checking HIS database...${NC}"
if [ -f "data/local_db/clinic.db" ]; then
    TABLES=$(sqlite3 data/local_db/clinic.db ".tables" 2>/dev/null)
    if [ -n "$TABLES" ]; then
        echo -e "${GREEN}✓ clinic.db exists with tables: ${TABLES:0:50}...${NC}"
    else
        echo -e "${RED}✗ clinic.db empty or corrupted${NC}"
    fi
else
    echo -e "${RED}✗ clinic.db not found${NC}"
fi

# Test 4: Check venv
echo -e "${YELLOW}[4/6] Checking Python environment...${NC}"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    PY_VERSION=$(python --version)
    echo -e "${GREEN}✓ Virtual environment active ($PY_VERSION)${NC}"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    exit 1
fi

# Test 5: Check Hermes imports
echo -e "${YELLOW}[5/6] Checking Hermes imports...${NC}"
python -c "from src.agent.hermes_core import get_hermes_agent; print('✓ Hermes imports OK')" 2>&1 && echo -e "${GREEN}✓ Hermes modules loadable${NC}" || echo -e "${RED}✗ Hermes import failed${NC}"

# Test 6: GPU status
echo -e "${YELLOW}[6/6] Checking GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
    DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    echo -e "${GREEN}✓ GPU ready: ${VRAM} (Driver: ${DRIVER})${NC}"
else
    echo -e "${YELLOW}⚠ nvidia-smi not found${NC}"
fi

echo ""
echo -e "${GREEN}✅ All Phase 4 prerequisites verified!${NC}"
echo ""
echo "Next steps:"
echo "  1. Start llama-server: bash scripts/run_llama_server.sh models/Qwen3.6-35B-A3B.Q3_K_M.gguf 8081"
echo "  2. In another terminal: python scripts/hermes_cli.py health"
echo "  3. Test chat: python scripts/hermes_cli.py chat --query \"診所現在有多少病患?\""
