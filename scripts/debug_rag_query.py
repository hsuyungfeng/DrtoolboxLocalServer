#!/usr/bin/env python3
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from src.rag_engine import RAGEngine

def main():
    rag = RAGEngine()
    query = "我偏頭痛三天了，可以吃什麼藥？"
    print("=== Sending Query directly to RAGEngine ===")
    response, score = rag.query_integrated(query, route="general")
    print(f"Confidence Score: {score}")
    print("Response:")
    print("-" * 50)
    print(response)
    print("-" * 50)

if __name__ == "__main__":
    main()
