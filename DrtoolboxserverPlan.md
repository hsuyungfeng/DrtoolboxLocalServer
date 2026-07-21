# DrtoolboxLocalServer — 診所客服機器訓練與資料採集計畫書

## Executive Summary | 執行摘要

**DrtoolboxLocalServer** has been redesigned to focus on **Customer Service Machine Training and Data Collection (客服機器訓練與資料採集)**. The platform transitions from traditional vector-based RAG to a cutting-edge **Vectorless, Reasoning-based RAG** architecture using **VectifyAI/PageIndex** combined with a high-performance **SQLite Graph-RAG** engine (integrating 300k+ relationships of medical knowledge) and **SoapVoice** clinical speech processing. To maintain full data privacy, the platform continues to utilize **Local LLMs (Qwen (llama-qwen) via llama.cpp)** to power the reasoning engine and retains the **Hermes Agent** for intelligent tasks and system orchestration, while providing a robust pipeline for collecting and training on customer service interactions.

**DrtoolboxLocalServer** 已重新設計，專注於**客服機器訓練與資料採集**。平台從傳統的基於向量的 RAG 轉向使用 **VectifyAI/PageIndex** 的前沿**無向量、基於推理的 RAG** 架構，並結合了高效的 **SQLite Graph-RAG** 圖語義檢索引擎（融合了 30 萬條醫療關係）與 **SoapVoice** 臨床語音處理技術。為了維持完整的資料隱私，平台繼續使用**本地 LLM (透過 llama.cpp 運行的 Qwen (llama-qwen))** 來驅動推理引擎，並保留 **Hermes 代理**用於智能任務和系統編排，同時為收集和訓練客服交互提供了穩健的管道。

---

## 1. Core Components | 核心組件

### 1.1 PageIndex Reasoning-based RAG | 基於推理的無向量 RAG (PageIndex)

* **Objective**: Utilize VectifyAI/PageIndex to provide highly accurate, context-aware answers to patient inquiries without chunking or vector databases.
* **目標**: 利用 VectifyAI/PageIndex 提供針對患者查詢的高準確度、具備上下文意識的解答，無需進行文本分塊 (chunking) 或使用向量數據庫。
* **Features**:
  * **Hierarchical Tree Indexing**: Generate a "Table-of-Contents" tree structure from clinic manuals and documents.
    * 層級樹狀索引：從診所手冊和文檔生成“目錄”樹結構。
  * **LLM Tree Search**: Navigate the index using Local LLM reasoning for precise knowledge extraction.
    * LLM 樹搜索：使用本地 LLM 推理導航索引以進行精確的知識提取。
  * **Elimination of Vector DBs**: Replaced by structural and semantic tree parsing.
    * 淘汰向量數據庫 (Chroma/FAISS)：被結構化和語義樹解析取代。

### 1.2 SQLite Graph-RAG Engine | 醫療知識圖譜檢索 (Graph-RAG)

* **Objective**: Integrate massive structured medical relationships (from Neo4j & Jena Fuseki RDF ontologies) directly into SQLite to allow zero-dependency multi-hop reasoning.
* **目標**: 將龐大的結構化醫療關係（源自 Neo4j 與 Jena Fuseki RDF 本體）直接整合至本地 SQLite，實現零依賴的多步圖譜推導。
* **Features**:
  * **Unified Relational Graph**: Stores nodes (`medical_nodes`) and relationships (`medical_edges`) in the local `clinic.db` without running heavy Java Jena Fuseki or Neo4j servers.
    * 統一關係型圖譜：在本地 `clinic.db` 中存儲節點與邊，免去運行繁重的 Java Fuseki 或 Neo4j 服務。
  * **Rule-based & LLM Hybrid Matching**: Integrates jieba part-of-speech (posseg) tagging and REfO (Regular Expression for Objects) patterns for ultra-fast, deterministic rule matching (e.g., matching dosage, side effects, complications) combined with LLM fallback.
    * 規則與 LLM 混合匹配：結合 jieba 詞性標記與 REfO 物件正則表達式，進行極速且確定性的規則查詢（例如匹配用藥、併發症等），並以 LLM 作為語意補全的後備。
  * **Double Graph Fusion**: Merges Neo4j's 300k relationships and Jena's drug ontologies into a unified medical query engine.
    * 雙圖譜融合：將 Neo4j 的 30 萬條醫學關係與 Jena 的藥物本體庫融合成單一的醫學諮詢引擎。

### 1.3 SoapVoice Clinical Assistant Module | SoapVoice 語音病歷與字典集成

* **Objective**: Integrate clinical-grade speech processing and comprehensive medical databases into the doctor/staff workflow.
* **目標**: 將臨床級語音處理技術與豐富的醫學資料庫整合至醫生與員工工作流中。
* **Features**:
  * **Voice-to-SOAP (ASR + LLM)**: Translates doctor's speech consults into standardized SOAP (Subjective, Objective, Assessment, Plan) formatted medical records.
    * 語音轉 SOAP：將醫生的口述看診記錄轉換為標準化 SOAP 格式病歷。
  * **Medical Databases Integration**: Combines SoapVoice's 9.6M ICD-10 diagnoses codes, 1.2M drugs list, and 2,102 clinical orders into `clinic.db`.
    * 醫學資料庫集成：將 SoapVoice 擁有的 9.6 萬條 ICD-10 代碼、1.2 萬條藥品列表及 2,102 條臨床處置集成入 `clinic.db`。

### 1.4 Data Collection Pipeline | 資料採集管道

* **Objective**: Systematically collect patient inquiries, system responses, and human-in-the-loop corrections to train future models.
* **目標**: 系統地收集患者查詢、系統響應 and 人在迴路 (human-in-the-loop) 的修正，以訓練未來的模型。
* **Features**:
  * **Centralized Data Storage**: All conversation logs and feedback stored in the `/data` directory.
    * 集中式數據存儲：所有對話日誌和反饋均存存储在 `/data` 目錄中。
  * **Quality Scoring**: Clinic staff can rate and correct chatbot responses.
    * 質量評分：診所員工可以對聊天機器人的響應進行評分和糾正。
  * **Dataset Export**: Automatically format collected data into JSONL/instruction-tuning formats for LLM fine-tuning.
    * 數據集導出：自動將收集的數據格式化為 JSONL/指令微調格式，以進行 LLM 微調。

### 1.5 Local LLM Infrastructure | 本地 LLM 基礎設施

* **Objective**: Serve large language models locally to ensure data privacy and zero cloud dependency.
* **目標**: 在本地提供大型語言模型服務，以確保數據隱私和零雲端依賴。
* **Features**:
  * **Local Engine**: `llama.cpp` for optimized local inference.
    * 本地引擎：使用 `llama.cpp` 進行優化的本地推理。
  * **Model**: `Qwen (llama-qwen)` model running on local GPU.
    * 模型：在本地 GPU 上運行 `Qwen (llama-qwen)` 模型。
  * **Powering PageIndex**: The local LLM acts as the reasoning engine for PageIndex tree search and generation.
    * 驅動 PageIndex：本地 LLM 充當 PageIndex 樹搜索和生成的推理引擎。

### 1.6 Hermes Agent | Hermes 代理

* **Objective**: Retain intelligent agent capabilities for data analysis, context processing, and task orchestration.
* **目標**: 保留智能代理功能，用於數據分析、上下文處理和任務編排。
* **Features**:
  * **Task Orchestration**: Hermes agent handles complex workflows beyond simple Q&A.
    * 任務編排：Hermes 代理處理簡單問答之外的複雜工作流程。
  * **System Integration**: Connects with HIS or local tools when necessary to retrieve dynamic context.
    * 系統整合：必要時與 HIS 或本地工具連接以檢索動態上下文。

---

## 2. Architecture Overview | 架構概述

```text
┌─────────────────────────────────────────────────────────────┐
│                    Patient/Staff Interfaces                 │
├──────────────┬──────────────────────────────────────────────┤
│ LINE Bot     │ Web Chat / Staff Correction Dashboard        │
└───────┬──────┴──────────────────────┬───────────────────────┘
        │                             │
┌───────▼─────────────────────────────▼───────────────────────┐
│                 Data Collection Engine (/data)              │
│   (Logs, Queries, Corrections, SOAP Voice, Training Data)   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                 Hermes Agent Orchestration                  │
│  (Task routing, SOAP generation, Brand & Price Redaction)   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│             Deep Hybrid Reasoning (RAG Engine)              │
│ ┌──────────────────────┐ ┌────────────────────────────────┐ │
│ │ PageIndex RAG        │ │ SQLite Graph-RAG & Dicts       │ │
│ │ (Hierarchy Tree)     │ │ (Neo4j, Jena, SoapVoice DB)    │ │
│ └──────────┬───────────┘ └──────────────┬─────────────────┘ │
│            │                            │                   │
│            └──────────────┬─────────────┘                   │
│                           │                                 │
│            ┌──────────────▼─────────────┐                   │
│            │ Local LLM Inference        │                   │
│            │ (Qwen-35B via llama.cpp)   │                   │
│            └────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack | 技術棧

### RAG, Graph & Voice | 檢索、圖譜與語音
* **PageIndex Engine**: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex) (Reasoning-based RAG, hierarchical tree index)
* **Graph Engine**: Custom `GraphRAGEngine` utilizing SQLite (`clinic.db`) tables
* **Speech Processing**: Local `Faster-Whisper` / `whisper.cpp` ASR engine
* **Parser Engine**: `jieba` + `jieba.posseg` + `refo` (Regular Expression for Objects)
* **Data Sources**: Clinic manuals, Neo4j `medical.json`, Jena RDF `kgdrug.ttl`, SoapVoice `medical.db` (ICD-10/Drugs)

### Local LLM & AI | 本地 LLM 與 AI
* **LLM Engine**: `llama.cpp`
* **Model**: `Qwen (llama-qwen)` (G Gemma-4 locally supported for offline clinic generation)
* **Agent Framework**: Hermes Agent

### Data Collection & Backend | 資料採集與後端
* **Storage**: SQLite + JSON/JSONL within `/data`
* **Backend Framework**: Flask (Python 3.10+)
* **Integration**: LINE Bot SDK, Webhooks, SOAP endpoints

---

## 4. Implementation Phases | 實施階段

### Phase 1: Environment, Local LLM & PageIndex Setup | 環境、本地 LLM 與 PageIndex 設置
* **目標**: 準備本地推理環境並導入 PageIndex。
* Setup `llama.cpp` and download the `Qwen (llama-qwen)` model.
* Install and configure `pageindex` package to utilize the local `llama.cpp` API for reasoning.
* Generate first hierarchical tree from sample clinic documents.

### Phase 2: Data Collection Pipeline | 資料採集管道建置
* **目標**: 建立 `/data` 的日誌記錄與反饋機制。
* Implement message interception and logging to `/data`.
* Create a simple feedback loop for staff to correct answers.
* Script to parse `/data` logs into training pairs.

### Phase 3: Web Dashboard & Feedback Loop | 網頁控制台與反饋迴圈
* **目標**: 實作 Glassmorphism 風格網頁後台，便於診所人員對 QA 進行標記與修正。
* Build a responsive dark-mode dashboard for data curation.
* Enable correction loop that writes back human answers into training pairs.
* Connect LINE/Web chat to the Hermes Agent pipeline.

### Phase 4: Integration of Medical Knowledge Graph | 醫療知識圖譜與雙圖譜融合
* **目標**: 導入 Neo4j 與 Jena Fuseki 知識庫，實作高效、零依賴的本地 Graph-RAG。
* Setup SQLite schema (`medical_nodes`, `medical_edges`, `disease_details`) to deprecate Neo4j and Fuseki servers.
* Implement `rdflib` parsing of `kgdrug.ttl` and write into unified SQLite.
* Port `refo` patterns for deterministic question-to-SQL logic in `GraphRAGEngine`.
* Hook Graph-RAG context into Hermes routing workflow with strict brand and price redaction.

### Phase 5: Speech-to-SOAP Clinical Integration | 臨床語音病歷與字典整合
* **目標**: 串接 SoapVoice 語音生成引擎與整合醫療字典，提升臨床診斷與病歷記錄效率。
* Merge SoapVoice's `medical.db` (96,802 ICD-10 codes, 12,042 drugs, 2,102 orders) into `clinic.db`.
* Build a frontend tab for doctors to upload/record speech transcripts.
* Run local `Faster-Whisper` ASR and pass textual transcript to LLM to extract Subjective, Objective, Assessment, and Plan fields.
* Auto-save generated SOAP cases directly into HIS database for patient follow-up tracking.

---

## 5. Strategic Plan Improvements (Redesign) | 戰略計畫改進 (重新設計)

Based on the recent shift towards **Customer Service Machine Training & Data Collection**, the following major changes have been executed:
基於近期向**客服機器訓練與資料採集**的轉變，已執行以下重大變更：

1. **Retained Local LLM (Qwen (llama-qwen))**: Emphasizing data privacy, the project continues to run `llama.cpp` and the `Qwen (llama-qwen)` model locally. This local LLM acts as the core reasoning engine for the new RAG architecture.
   * **保留本地 LLM (Qwen (llama-qwen))**：強調數據隱私，項目繼續在本地運行 `llama.cpp` 和 `Qwen (llama-qwen)` 模型。此本地 LLM 充當新 RAG 架構的核心推理引擎。
2. **Replaced Heavy Graph Servers with SQLite**: Instead of running resource-heavy Neo4j and Jena Fuseki servers locally, both graphs have been flattened and compiled into standard SQLite tables inside `clinic.db`, ensuring a lightweight, zero-dependency deployment footprint.
   * **以 SQLite 取代重型圖資料庫服務**：不再於本地運作高資源消耗的 Neo4j 與 Jena Fuseki 伺服器，而是將雙圖譜提取並拍平導入 `clinic.db` 中的標準 SQLite 表，確保輕量化與零依賴的部署。
3. **Double Graph Fusion and REfO Integration**: Merged the entity relations from the two largest open-source medical graphs and added rule-based pattern matching (using `refo`) as a first-line query parser before fallback LLM parsing.
   * **雙圖譜融合與 REfO 整合**：融合兩大醫療圖譜的實體關係，並加入基於規則的模式比對（使用 `refo`）作為第一線查詢解析，隨後才降級至 LLM 解析。
4. **Clinical Speech Productivity Integration**: Merged the SoapVoice engine to provide doctors with speech-to-SOAP generation. This bridges patient customer service interactions with clinical HIS record generation under a privacy-first local architecture.
   * **臨床語音生產力整合**：融合 SoapVoice 引擎為醫生提供語音轉 SOAP 結構化病歷。這在隱私優先的本地架構下，將患者客服互動與臨床 HIS 記錄生成串接起來。
5. **Strict Brand & Price Compliance**: Hardcoded system policies and filters enforce redacting clinical pricing and keeping branding aligned with Zhiyan Aesthetic Clinic (緻妍診所).
   * **嚴格的品牌與價格合規**：硬性規定系統策略與過濾器，強制屏蔽醫療價格，並使品牌定位完全與「緻妍診所」保持一致。
