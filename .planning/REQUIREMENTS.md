# Requirements

## Epic 1: Knowledge Base & RAG Engine
- RQ-1.1: Implement `PageIndex` vectorless reasoning RAG architecture.
- RQ-1.2: Build a data ingestion pipeline to segregate Clinic Special Data (`/media/hsu/软件/行銷圖文檔案整理`) from General Medical Data.
- RQ-1.3: Integrate `hermes-agent` with `PageIndex` to dynamically route LINE/Web chat queries to the correct knowledge tree.

## Epic 2: Data Logging & Feedback Loop
- RQ-2.1: Implement a data-centric logging pipeline that saves all interactions as JSON in `/data`.
- RQ-2.2: Create a feedback loop allowing staff to correct LLM answers and seamlessly append them to the training dataset.

## Epic 3: Web Dashboard
- RQ-3.1: Build a Web Dashboard interface for clinic staff.
- RQ-3.2: Enable staff to view, search, edit, and export JSON training data from the dashboard.
