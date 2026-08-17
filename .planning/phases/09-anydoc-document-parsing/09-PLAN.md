# Phase 9 Plan: High-Speed Document Parsing & Markdown Normalization with Firecrawl Anydoc

## Goal
Integrate Firecrawl's Rust-based `anydoc` parser into the document ingestion pipeline (`src/data_loader.py`), converting `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.csv`, and `.odt` into clean, unified GitHub-Flavored Markdown (GFM) with preserved tables, while retaining `pytesseract` for scanned OCR and `faster-whisper` for audio.

---

## Tasks

### Task 1: AnydocParser Service (`src/services/anydoc_parser.py`)
- Implement `AnydocParser` class:
  - Detects `anydoc` CLI / Node execution.
  - Invokes parsing with timeout and robust error trapping.
  - Normalizes output to clean UTF-8 GitHub-Flavored Markdown (preserving tables, lists, and headers).
  - Returns `None` or raises gracefully on image-only/scanned documents to trigger downstream OCR.

### Task 2: Data Loader Pipeline Refactoring (`src/data_loader.py`)
- Update `extract_text_from_file(filepath)`:
  - Route supported office extensions (`.docx`, `.pptx`, `.xlsx`, `.doc`, `.ppt`, `.odt`, `.rtf`, `.csv`, `.pdf`) through `AnydocParser`.
  - If output text length < 15 or fails on scanned PDF, fallback to `_do_pdf_ocr(filepath)`.
  - Keep image files (`.jpg`, `.png`, `.jpeg`) mapped to `pytesseract` + vision analysis.
  - Keep audio/video files mapped to `faster-whisper`.

### Task 3: Dashboard Preview Endpoint (`src/api/routes/dashboard.py`)
- Add `POST /api/dashboard/documents/parse_preview` endpoint:
  - Accepts a file upload or file path and returns the rendered Markdown along with parsing duration (ms).

### Task 4: Unit Testing & Verification (`tests/test_anydoc_parser.py`)
- Create unit tests verifying:
  - DOCX & CSV table-to-markdown conversion.
  - Graceful fallback when parsing text files and mock documents.
  - Integration with `data_loader.extract_text_from_file`.

### Task 5: Full Regression Testing & Documentation
- Run `uv run env PYTHONPATH=. pytest tests/ -v` to ensure 100% test pass rate across the repository.
- Update `ROADMAP.md` and `STATE.md`.
