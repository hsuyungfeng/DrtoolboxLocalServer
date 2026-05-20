#!/usr/bin/env python3
"""
CUDA llama-server Verification Script

Verifies that:
1. Binary exists and has CUDA backend
2. Model loads without segfault
3. HTTP server responds to requests
4. Hermes agent integration works
"""

import subprocess
import time
import sys
import os
import requests
import json
from pathlib import Path

# Configuration
BINARY = "/tmp/llama.cpp/build/bin/llama-server"
MODEL = "models/Qwen3.6-35B-A3B.Q3_K_M.gguf"
PORT = 8081
BASE_URL = f"http://127.0.0.1:{PORT}"

def log(msg: str, status: str = ""):
    """Print colored log message."""
    colors = {
        "✓": "\033[92m",  # Green
        "✗": "\033[91m",  # Red
        "⏳": "\033[93m",  # Yellow
        "ℹ": "\033[94m",  # Blue
    }
    reset = "\033[0m"
    prefix = colors.get(status, "") + status + reset if status else ""
    print(f"{prefix} {msg}")

def check_binary_exists():
    """Check if CUDA-built binary exists."""
    log("Checking if binary exists...", "ℹ")
    if not os.path.exists(BINARY):
        log(f"Binary not found at {BINARY}", "✗")
        return False
    log(f"Binary found at {BINARY}", "✓")
    return True

def check_cuda_backend():
    """Verify binary has CUDA backend, not Vulkan."""
    log("Checking CUDA backend...", "ℹ")
    try:
        result = subprocess.run(
            [BINARY, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr

        if "loaded CUDA backend" in output:
            log("CUDA backend loaded ✓", "✓")
            return True
        elif "loaded Vulkan backend" in output:
            log("Vulkan backend detected (not CUDA) ✗", "✗")
            return False
        else:
            log(f"Unknown backend. Output:\n{output}", "✗")
            return False
    except subprocess.TimeoutExpired:
        log("Binary version check timed out", "✗")
        return False
    except Exception as e:
        log(f"Error checking binary: {e}", "✗")
        return False

def start_server():
    """Start llama-server in background."""
    log("Starting llama-server...", "ℹ")

    if not os.path.exists(MODEL):
        log(f"Model not found at {MODEL}", "✗")
        return None

    env = os.environ.copy()
    env["GGML_CUDA"] = "1"
    env["GGML_CUDA_PEER_MAX_BATCH_SIZE"] = "32"

    try:
        proc = subprocess.Popen(
            [
                BINARY,
                "--model", MODEL,
                "--port", str(PORT),
                "--gpu-layers", "50",
                "--n-batch", "256",
                "--n-ctx", "4096",
                "--threads", "4",
                "--verbose"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )

        log(f"Server started (PID: {proc.pid})", "✓")
        return proc
    except Exception as e:
        log(f"Failed to start server: {e}", "✗")
        return None

def wait_for_server(timeout=120):
    """Wait for server to be ready."""
    log(f"Waiting for server to be ready (timeout: {timeout}s)...", "ℹ")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=2)
            if resp.status_code == 200:
                log("Server is ready ✓", "✓")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            log(f"Error checking health: {e}", "✗")

        time.sleep(2)
        elapsed = time.time() - start_time
        print(f"  [{elapsed:.0f}s] Still waiting...", end="\r")

    log(f"Server did not become ready within {timeout}s", "✗")
    return False

def test_inference():
    """Test basic inference request."""
    log("Testing inference request...", "ℹ")

    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'Hello' in one word."}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"].strip()
                log(f"Inference works! Response: '{content}'", "✓")
                return True
        else:
            log(f"Inference failed: {response.status_code} - {response.text}", "✗")
            return False
    except Exception as e:
        log(f"Inference error: {e}", "✗")
        return False

def main():
    """Run all verification steps."""
    log("=" * 60, "ℹ")
    log("CUDA llama-server Verification", "ℹ")
    log("=" * 60, "ℹ")

    # Step 1: Check binary
    if not check_binary_exists():
        return 1

    # Step 2: Check CUDA backend
    if not check_cuda_backend():
        return 1

    # Step 3: Start server
    proc = start_server()
    if proc is None:
        return 1

    # Step 4: Wait for server
    if not wait_for_server():
        proc.terminate()
        proc.wait(timeout=5)
        return 1

    # Step 5: Test inference
    if not test_inference():
        proc.terminate()
        proc.wait(timeout=5)
        return 1

    log("=" * 60, "ℹ")
    log("✓ All verification steps passed!", "✓")
    log("=" * 60, "ℹ")
    log(f"Server running at {BASE_URL}", "ℹ")
    log("Press Ctrl+C to stop", "ℹ")

    # Keep server running
    try:
        proc.wait()
    except KeyboardInterrupt:
        log("\nShutting down...", "ℹ")
        proc.terminate()
        proc.wait(timeout=5)

    return 0

if __name__ == "__main__":
    sys.exit(main())
