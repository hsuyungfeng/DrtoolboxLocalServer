# Phase 9 Context: High-Speed Document Parsing & Markdown Normalization with Firecrawl Anydoc

## Phase Scope & Objectives
Integrate Firecrawl's open-source Rust-based document parser (`anydoc` / `firecrawl-anydoc`) into `src/data_loader.py` and the RAG ingestion pipeline.

### Key Goals:
1. **High-Speed Document Parsing**:
   - Replace legacy, slower Python parsers (`python-docx`, `python-pptx`, `PyPDF2`, LibreOffice headless `soffice`) with high-speed Rust-based `anydoc` (<5ms per document).
2. **Unified GitHub-Flavored Markdown (GFM) Normalization**:
   - Standardize all office documents (`.docx`, `.pptx`, `.xlsx`, `.pdf`, `.rtf`, `.odt`, `.csv`) into clean, consistent Markdown output.
   - Preserve critical medical tables, dosage charts, treatment protocols, and heading hierarchies for `PageIndex 2.0` tree construction and SQLite FTS5 search.
3. **Graceful Fallback & Separation of Concerns**:
   - Use `anydoc` as the primary document parser.
   - Retain `pytesseract` strictly for pure-image OCR and scanned PDF pages (<15 characters).
   - Retain `faster-whisper` strictly for audio/video transcription (`.mp4`, `.mp3`, `.wav`, `.m4a`).
   - Fallback to native Python parsers if `anydoc` binary is not found or encounters an unsupported file edge case.
4. **Automated Unit Testing & Verification**:
   - Unit tests covering `.docx`, `.pptx`, `.xlsx`, `.pdf` and table structure preservation.
