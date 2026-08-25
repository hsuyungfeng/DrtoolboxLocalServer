import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.rag.normalize import normalize_to_traditional

def test_normalize_simplified_to_traditional():
    simplified_text = "简称PAP，该患者需要前往医院就诊，发烧应尽早处理。"
    result = normalize_to_traditional(simplified_text)
    assert "簡稱" in result
    assert "該" in result
    assert "就診" in result
    assert "發燒" in result
    assert "PAP" in result


def test_normalize_empty_and_none():
    assert normalize_to_traditional("") == ""
    assert normalize_to_traditional(None) is None


def test_normalize_traditional_and_ocr_noise():
    mixed_text = "Mini-plastic Surgery UH - HARE 緻妍醫美診所 術後注意事項。"
    result = normalize_to_traditional(mixed_text)
    assert "緻妍醫美診所" in result
    assert "Mini-plastic Surgery" in result


def test_normalize_fallback_on_error(monkeypatch):
    import src.rag.normalize as norm_mod
    
    class BrokenConverter:
        def convert(self, text):
            raise RuntimeError("Fake conversion error")
            
    monkeypatch.setattr(norm_mod, "_converter", BrokenConverter())
    
    raw = "这是一段测试文本"
    # Should not raise, returns raw text gracefully
    assert normalize_to_traditional(raw) == raw
