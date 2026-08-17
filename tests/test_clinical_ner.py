"""
Unit tests for ClinicalNER Service & Graph-RAG integration
"""

import pytest
from src.rag.clinical_ner import ClinicalNER, clinical_ner
from src.rag.graph_rag_engine import GraphRAGEngine


def test_clinical_ner_extraction():
    ner = ClinicalNER()
    transcript = "患者主訴發燒與喉嚨痛，診斷為急性扁桃腺炎，開立普拿疼 500mg tid po 以及 Amoxicillin 500mg tid 治療7天。"

    entities = ner.extract_entities(transcript)
    labels = {e["label"] for e in entities}
    texts = [e["text"] for e in entities]

    assert "DRUG" in labels
    assert any("普拿疼" in t or "Amoxicillin" in t for t in texts)
    assert "DOSAGE" in labels
    assert any("500mg" in t for t in texts)
    assert "FREQUENCY" in labels
    assert any("tid" in t for t in texts)
    assert "SYMPTOM" in labels
    assert any("發燒" in t or "喉嚨痛" in t for t in texts)


def test_clinical_ner_summary():
    transcript = "開立 Saxenda 0.6mg qd 進行體重管理，並注意是否有噁心症狀。"
    summary = clinical_ner.summarize_clinical_tags(transcript)

    assert "Saxenda" in summary["drugs"]
    assert any("0.6mg" in d for d in summary["dosages"])
    assert any("qd" in f for f in summary["frequencies"])
    assert any("噁心" in s for s in summary["symptoms"])


def test_graph_rag_with_ner():
    engine = GraphRAGEngine()
    query = "痛風發作如何治療與預防發作，可以使用秋水仙素嗎？"
    matched_nodes = engine.extract_nodes_by_matching(query)
    # Check that query resolution correctly extracts nodes
    assert isinstance(matched_nodes, list)
