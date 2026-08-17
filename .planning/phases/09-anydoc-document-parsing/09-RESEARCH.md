# Phase 9 Research: Firecrawl Anydoc Document Parsing Architecture

## Architecture Findings

### 1. Firecrawl Anydoc Capabilities
- **CLI & Bindings**:
  - `npx -y @firecrawl/anydoc <file>` or Node package `@firecrawl/anydoc`
  - Zero-cloud, 100% on-device local execution with Rust core.
  - Automatic format detection for `doc`, `docx`, `odt`, `pdf`, `ppt`, `pptx`, `rtf`, `epub`, `xlsx`, `ods`, `odp`, `csv`.
- **Output Quality**:
  - Produces pure GitHub-Flavored Markdown (GFM).
  - Converts tables with rows and columns into standard markdown pipes (`| header1 | header2 |`).
  - Converts document headers into `#`, `##`, `###` headings suitable for PageIndex tree hierarchy.
- **Handling of Scanned Documents**:
  - Scanned/image-only PDFs exit with error code or return minimal text (<15 chars), which our architecture smoothly hands over to `_do_pdf_ocr(filepath)` (Tesseract).

### 2. Integration into `src/data_loader.py`
- We can create a dedicated `AnydocParser` in `src/services/anydoc_parser.py` or directly integrate inside `src/data_loader.py`:
  - `parse_document_with_anydoc(filepath: str) -> Optional[str]`
  - Runs anydoc parsing with timeout (e.g. 5s) and UTF-8 decode.
  - If output length >= 15 chars and valid Markdown, returns it.
  - If anydoc fails, gracefully falls back to native `python-docx`, `python-pptx`, `PyPDF2`, or LibreOffice.
  - If document is scanned / pure image, triggers `_do_pdf_ocr(filepath)` using `pytesseract`.
  - Audio/video files (`.mp4`, `.mp3`, `.wav`, `.m4a`, `.flv`) continue directly to `faster-whisper`.
