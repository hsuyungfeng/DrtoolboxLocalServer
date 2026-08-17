"""
Unit tests for PrivacyService (PII / PHI De-identification)
"""

import os
import json
import tempfile
import pytest
from src.services.privacy_service import PrivacyService


@pytest.fixture
def privacy_svc():
    return PrivacyService()


def test_extract_pii_taiwan_identifiers(privacy_svc):
    sample_text = "病患姓名：王大明，身分證字號 A123456789，電話 0912-345-678，生日 1985-05-12，病歷號 MRN-998822。"
    entities = privacy_svc.extract_pii(sample_text)
    labels = [e["label"] for e in entities]
    texts = [e["text"] for e in entities]

    assert "ID" in labels
    assert "A123456789" in texts or any("A123456789" in t for t in texts)
    assert "PHONE" in labels
    assert any("0912" in t for t in texts)
    assert "DATE" in labels
    assert "1985-05-12" in texts


def test_anonymize_text_mask(privacy_svc):
    sample_text = "患者：陳志豪，手機 0988-123-456，身分證 B223456789。"
    masked = privacy_svc.anonymize_text(sample_text, method="mask")

    assert "0988-123-456" not in masked
    assert "B223456789" not in masked
    assert "[PHONE]" in masked or "[ID]" in masked


def test_anonymize_text_replace(privacy_svc):
    sample_text = "病患：林美麗，電話 0933-987-654。"
    replaced = privacy_svc.anonymize_text(sample_text, method="replace")

    assert "0933-987-654" not in replaced


def test_anonymize_text_hash(privacy_svc):
    sample_text = "身分證字號 A123456789"
    hashed = privacy_svc.anonymize_text(sample_text, method="hash")

    assert "A123456789" not in hashed
    assert "[ID_" in hashed


def test_anonymize_conversation(privacy_svc):
    conv = {
        "timestamp": "2026-08-17T12:00:00Z",
        "messages": [
            {"role": "user", "content": "你好，我是病患王小明，電話 0911222333，我想詢問減重療程。"},
            {"role": "assistant", "content": "王先生您好，為您介紹 Saxenda 療程。"}
        ],
        "metadata": {"user_id": "test"}
    }
    anonymized = privacy_svc.anonymize_conversation(conv, method="mask")

    assert "0911222333" not in anonymized["messages"][0]["content"]
    assert "[PHONE]" in anonymized["messages"][0]["content"]
    assert anonymized["metadata"]["user_id"] == "test"


def test_anonymize_jsonl_file(privacy_svc):
    records = [
        {"messages": [{"role": "user", "content": "姓名：張三，電話 0912345678"}]},
        {"messages": [{"role": "user", "content": "身分證 A123456789 預約門診"}]}
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f_in:
        for r in records:
            f_in.write(json.dumps(r) + "\n")
        in_path = f_in.name

    out_path = in_path + ".clean.jsonl"
    try:
        count = privacy_svc.anonymize_jsonl_file(in_path, out_path, method="mask")
        assert count == 2

        with open(out_path, "r", encoding="utf-8") as f_out:
            lines = [json.loads(line) for line in f_out]
            assert "0912345678" not in lines[0]["messages"][0]["content"]
            assert "A123456789" not in lines[1]["messages"][0]["content"]
    finally:
        if os.path.exists(in_path):
            os.remove(in_path)
        if os.path.exists(out_path):
            os.remove(out_path)
