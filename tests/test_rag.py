import pytest
from src.rag_engine import RAGEngine

class DummyLLM:
    def generate(self, prompt, **kwargs):
        return "Dummy response based on reasoning."

def test_rag_engine_initialization(monkeypatch):
    # Mock the singleton llm_instance to avoid loading actual model during tests
    monkeypatch.setattr("src.rag_engine.llm_instance", DummyLLM())
    
    engine = RAGEngine()
    assert engine.special_index is not None
    assert engine.general_index is not None
