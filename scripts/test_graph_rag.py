#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script for Graph-RAG Retrieval and Integration.
"""

import sys
import os

# Set path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from src.rag.graph_rag_engine import GraphRAGEngine
from src.rag_engine import RAGEngine

def test_graph_rag_direct():
    print("=== Testing GraphRAGEngine Direct Query ===")
    engine = GraphRAGEngine()
    
    # 1. Test node extraction
    query = "請問百日咳有什麼併發症和推薦的藥品？"
    matched = engine.extract_nodes_by_matching(query)
    print(f"Query: '{query}'")
    print(f"Matched Nodes: {matched}")
    
    assert any(n["name"] == "百日咳" for n in matched), "Failed to match disease '百日咳' in query"
    print("✓ Node extraction successful.")
    
    # 2. Test context generation
    context = engine.query_graph_context(query)
    print("\nGenerated Graph Context:")
    print("-" * 50)
    print(context)
    print("-" * 50)
    
    assert "百日咳" in context, "Context does not mention '百日咳'"
    assert "常用藥品" in context or "推薦藥品" in context or "伴隨症狀" in context, "Context does not contain relationships"
    print("✓ Relationship retrieval and context formatting successful.")

def test_rag_engine_integration():
    print("\n=== Testing RAGEngine Integration ===")
    rag = RAGEngine()
    
    # Query integrating local SQLite, simple index, and graph RAG
    query = "百日咳的預防措施與推薦藥品是什麼？"
    
    # Mocking reasoner's reason_chat to trace prompt inputs
    original_reason_chat = rag.reasoner.reason_chat
    captured_messages = []
    
    def mock_reason_chat(messages):
        captured_messages.extend(messages)
        return "MOCKED_RESPONSE: 這是百日咳的答覆。"
        
    rag.reasoner.reason_chat = mock_reason_chat
    
    response = rag.query_integrated(query)
    print(f"Query: '{query}'")
    print(f"Mocked Response: {response}")
    
    # Verify that Graph-RAG context was injected
    system_message = next((m["content"] for m in captured_messages if m["role"] == "system"), "")
    print("\nSystem Message Snippet:")
    print(system_message[:300] + "...")
    
    assert "【關聯資料來源：醫學知識圖譜 (關聯推導結果)】" in system_message, "Graph-RAG source missing from system prompt"
    assert "百日咳" in system_message, "Disease context not injected into system prompt"
    print("✓ Graph-RAG integration into RAGEngine system prompt verified.")

def main():
    try:
        test_graph_rag_direct()
        test_rag_engine_integration()
        print("\n🎉 ALL GRAPH-RAG VERIFICATION TESTS PASSED SUCCESSFULLY!")
    except AssertionError as e:
        print(f"\n❌ Test verification failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
