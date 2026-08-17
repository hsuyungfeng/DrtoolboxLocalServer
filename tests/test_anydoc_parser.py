"""
Unit tests for AnydocParser Service and Document Ingestion Pipeline
"""

import os
import tempfile
import pytest
from src.services.anydoc_parser import AnydocParser, anydoc_parser
from src.data_loader import extract_text_from_file


@pytest.fixture
def parser():
    return AnydocParser()


def test_is_supported_extensions(parser):
    assert parser.is_supported("protocol.docx") is True
    assert parser.is_supported("presentation.pptx") is True
    assert parser.is_supported("medication_list.xlsx") is True
    assert parser.is_supported("records.pdf") is True
    assert parser.is_supported("pricing.csv") is True
    assert parser.is_supported("document.odt") is True
    assert parser.is_supported("image.png") is False
    assert parser.is_supported("audio.mp3") is False


def test_parse_csv_table(parser):
    csv_content = "療程名稱,建議次數,間隔時間\n皮秒雷射,3次,4週\n肉毒桿菌素,1次,4-6個月\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_csv = f.name

    try:
        res = parser.parse(temp_csv)
        assert res["success"] is True
        assert "皮秒雷射" in res["markdown"]
        assert "肉毒桿菌素" in res["markdown"]
        assert res["elapsed_ms"] >= 0
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)


def test_parse_non_existent_file(parser):
    res = parser.parse("/path/to/non_existent_file.docx")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_extract_text_from_txt_file():
    sample_text = "緻妍診所術後衛教說明：請於術後一週內避免高溫泡溫泉。"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(sample_text)
        temp_txt = f.name

    try:
        extracted = extract_text_from_file(temp_txt)
        assert sample_text in extracted
    finally:
        if os.path.exists(temp_txt):
            os.remove(temp_txt)


def test_extract_text_from_csv_via_data_loader():
    csv_content = "藥品名稱,規格,劑量\n普拿疼,500mg,1# tid\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_csv = f.name

    try:
        extracted = extract_text_from_file(temp_csv)
        assert "普拿疼" in extracted
        assert "500mg" in extracted
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
