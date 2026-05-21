# DrtoolboxLocalServer — 診所客服機器訓練與資料採集計畫書

## Executive Summary | 執行摘要

**DrtoolboxLocalServer** has been redesigned to focus on **Customer Service Machine Training and Data Collection (客服機器訓練與資料採集)**. The platform transitions from traditional vector-based RAG to a cutting-edge **Vectorless, Reasoning-based RAG** architecture using **VectifyAI/PageIndex**. To maintain full data privacy, the platform continues to utilize **Local LLMs (Qwen (llama-qwen) via llama.cpp)** to power the reasoning engine and retains the **Hermes Agent** for intelligent tasks and system orchestration, while providing a robust pipeline for collecting and training on customer service interactions.

**DrtoolboxLocalServer** 已重新設計，專注於**客服機器訓練與資料採集**。平台從傳統的基於向量的 RAG 轉向使用 **VectifyAI/PageIndex** 的前沿**無向量、基於推理的 RAG** 架構。為了維持完整的資料隱私，平台繼續使用**本地 LLM (透過 llama.cpp 運行的 Qwen (llama-qwen))** 來驅動推理引擎，並保留 **Hermes 代理**用於智能任務和系統編排，同時為收集和訓練客服交互提供了穩健的管道。

---

## 1. Core Components | 核心組件

### 1.1 PageIndex Reasoning-based RAG | 基於推理的無向量 RAG (PageIndex)

**Objective**: Utilize VectifyAI/PageIndex to provide highly accurate, context-aware answers to patient inquiries without chunking or vector databases.
**目標**: 利用 VectifyAI/PageIndex 提供針對患者查詢的高準確度、具備上下文意識的解答，無需進行文本分塊 (chunking) 或使用向量數據庫。

**Features**:
- **Hierarchical Tree Indexing**: Generate a "Table-of-Contents" tree structure from clinic manuals and documents.
  - 層級樹狀索引：從診所手冊和文檔生成“目錄”樹結構。
- **LLM Tree Search**: Navigate the index using Local LLM reasoning for precise knowledge extraction.
  - LLM 樹搜索：使用本地 LLM 推理導航索引以進行精確的知識提取。
- **Elimination of Vector DBs**: Replaced by structural and semantic tree parsing.
  - 淘汰向量數據庫 (Chroma/FAISS)：被結構化和語義樹解析取代。

### 1.2 Data Collection Pipeline | 資料採集管道

**Objective**: Systematically collect patient inquiries, system responses, and human-in-the-loop corrections to train future models.
**目標**: 系統地收集患者查詢、系統響應和人在迴路 (human-in-the-loop) 的修正，以訓練未來的模型。

**Features**:
- **Centralized Data Storage**: All conversation logs and feedback stored in the `/data` directory.
  - 集中式數據存儲：所有對話日誌和反饋均存儲在 `/data` 目錄中。
- **Quality Scoring**: Clinic staff can rate and correct chatbot responses.
  - 質量評分：診所員工可以對聊天機器人的響應進行評分和糾正。
- **Dataset Export**: Automatically format collected data into JSONL/instruction-tuning formats for LLM fine-tuning.
  - 數據集導出：自動將收集的數據格式化為 JSONL/指令微調格式，以進行 LLM 微調。

### 1.3 Local LLM Infrastructure | 本地 LLM 基礎設施

**Objective**: Serve large language models locally to ensure data privacy and zero cloud dependency.
**目標**: 在本地提供大型語言模型服務，以確保數據隱私和零雲端依賴。

**Features**:
- **Local Engine**: `llama.cpp` for optimized local inference.
  - 本地引擎：使用 `llama.cpp` 進行優化的本地推理。
- **Model**: `Qwen (llama-qwen)` model running on local GPU.
  - 模型：在本地 GPU 上運行 `Qwen (llama-qwen)` 模型。
- **Powering PageIndex**: The local LLM acts as the reasoning engine for PageIndex tree search and generation.
  - 驅動 PageIndex：本地 LLM 充當 PageIndex 樹搜索和生成的推理引擎。

### 1.4 Hermes Agent | Hermes 代理

**Objective**: Retain intelligent agent capabilities for data analysis, context processing, and task orchestration.
**目標**: 保留智能代理功能，用於數據分析、上下文處理和任務編排。

**Features**:
- **Task Orchestration**: Hermes agent handles complex workflows beyond simple Q&A.
  - 任務編排：Hermes 代理處理簡單問答之外的複雜工作流程。
- **System Integration**: Connects with HIS or local tools when necessary to retrieve dynamic context.
  - 系統整合：必要時與 HIS 或本地工具連接以檢索動態上下文。

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
│        (Logs, Queries, Corrections, Training Datasets)      │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                 Hermes Agent Orchestration                  │
│       (Task management, Routing, Dynamic Context)           │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                 PageIndex RAG Engine                        │
│ ┌──────────────────────┐ ┌────────────────────────────────┐ │
│ │ Document Processing  │ │ Local LLM Reasoning            │ │
│ │ (Tree Construction)  │ │ (Qwen (llama-qwen) via llama.cpp)    │ │
│ └──────────────────────┘ └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack | 技術棧

### Vectorless Retrieval | 無向量檢索
- **Engine**: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex)
- **Concept**: Reasoning-based RAG, hierarchical tree index, no chunking.
- **Data Source**: Clinic rules, operational guides, medical FAQs.

### Local LLM & AI | 本地 LLM 與 AI
- **LLM Engine**: `llama.cpp`
- **Model**: `Qwen (llama-qwen)`
- **Agent Framework**: Hermes Agent

### Data Collection & Backend | 資料採集與後端
- **Storage**: JSON/JSONL within `/data`
- **Backend Framework**: Flask or FastAPI (Python)
- **Integration**: LINE Bot SDK, Webhooks.

---

## 4. Implementation Phases | 實施階段

### Phase 1: Environment, Local LLM & PageIndex Setup | 環境、本地 LLM 與 PageIndex 設置
**目標**: 準備本地推理環境並導入 PageIndex。
- Setup `llama.cpp` and download the `Qwen (llama-qwen)` model.
- Install and configure `pageindex` package to utilize the local `llama.cpp` API for reasoning.
- Generate first hierarchical tree from sample clinic documents.

### Phase 2: Data Collection Pipeline | 資料採集管道建置
**目標**: 建立 `/data` 的日誌記錄與反饋機制。
- Implement message interception and logging to `/data`.
- Create a simple feedback loop for staff to correct answers.
- Script to parse `/data` logs into training pairs.

### Phase 3: Integration & Testing | 整合與測試
**目標**: 串接 Hermes 代理、PageIndex 檢索與前端介面。
- Integrate Hermes Agent to route queries to PageIndex or handle dynamic tasks.
- Connect LINE/Web chat to the Hermes Agent pipeline.
- Run baseline testing on accuracy and local inference latency.

---

## 5. Strategic Plan Improvements (Redesign) | 戰略計畫改進 (重新設計)

Based on the recent shift towards **Customer Service Machine Training & Data Collection**, the following major changes have been executed:
基於近期向**客服機器訓練與資料採集**的轉變，已執行以下重大變更：

1. **Retained Local LLM (Qwen (llama-qwen))**: Emphasizing data privacy, the project continues to run `llama.cpp` and the `Qwen (llama-qwen)` model locally. This local LLM acts as the core reasoning engine for the new RAG architecture.
   - **保留本地 LLM (Qwen (llama-qwen))**：強調數據隱私，項目繼續在本地運行 `llama.cpp` 和 `Qwen (llama-qwen)` 模型。此本地 LLM 充當新 RAG 架構的核心推理引擎。
2. **Removed Vector Databases**: `clinic.db`, Chroma, and FAISS are deprecated. PageIndex's native tree-structure eliminates the need for vector similarity search, relying instead on the local LLM's reasoning capabilities.
   - **移除向量數據庫**：棄用 `clinic.db`、Chroma 和 FAISS。PageIndex 的原生樹結構消除了對向量相似性搜索的需求，轉而依賴本地 LLM 的推理能力。
3. **Data-Centric Focus**: The `/data` folder is now the core asset. All efforts will prioritize capturing high-quality question-answer pairs to fine-tune future models.
   - **以數據為中心**：`/data` 文件夾現在是核心資產。所有工作都將優先捕捉高質量的問答對，以微調未來的模型。
4. **Hermes Agent Orchestration**: Hermes Agent remains an integral part of the system, responsible for task routing and integrating with the PageIndex backend.
   - **Hermes 代理編排**：Hermes 代理仍然是系統不可或缺的一部分，負責任務路由並與 PageIndex 後端整合。
