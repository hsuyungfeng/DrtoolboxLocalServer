#!/usr/bin/env python3
"""
Benchmark script to measure latency of Chinese embedding models on CPU.
"""

import time
import sentence_transformers

MODELS = [
    "BAAI/bge-small-zh-v1.5",
    "BAAI/bge-m3",
]

TEST_QUERIES = [
    "肉毒桿菌術後多久可以洗臉？",
    "玻尿酸過敏怎麼辦？",
    "雷射術後保養注意事項",
]

def benchmark_model(model_name: str, runs: int = 20):
    print(f"\n--- Benchmarking: {model_name} ---")
    model = sentence_transformers.SentenceTransformer(model_name, device="cpu")
    
    # Warmup
    _ = model.encode(TEST_QUERIES)
    
    # Timing runs
    latencies = []
    for _ in range(runs):
        start = time.perf_counter()
        _ = model.encode(TEST_QUERIES)
        latencies.append((time.perf_counter() - start) * 1000.0) # in ms
        
    avg_ms = sum(latencies) / len(latencies)
    print(f"Model: {model_name} | Avg latency over {runs} batches (3 queries/batch): {avg_ms:.2f} ms")
    return avg_ms

def main():
    results = {}
    for model_name in MODELS:
        results[model_name] = benchmark_model(model_name)
        
    print("\n=== Benchmark Summary ===")
    for model_name, avg_ms in results.items():
        print(f"{model_name}: {avg_ms:.2f} ms")

if __name__ == "__main__":
    main()
