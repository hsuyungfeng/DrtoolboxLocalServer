# DrtoolboxLocalServer — 診所本地智能平台計畫書

## Executive Summary | 執行摘要

**DrtoolboxLocalServer** is a comprehensive local clinic intelligence platform designed to deliver medical AI capabilities without cloud dependency. The platform integrates RAG-based medical chatbots, Hermes agent for data analysis, multi-channel patient communication, and local LLM inference on available GPU hardware.

**DrtoolboxLocalServer** 是一個完整的本地診所智能平台，旨在不依賴雲端的情況下提供醫療人工智能功能。該平台整合了基於RAG的醫療聊天機器人、用於數據分析的Hermes代理、多渠道患者通信，以及在現有GPU硬件上的本地LLM推理。

---

## 1. Core Components | 核心組件

### 1.1 Medical RAG Chatbot | 醫療知識檢索增強對話機器人

**Objective**: Enable clinic and patients to query medical knowledge from clinic-specific documents

**目標**: 使診所和患者能夠從診所特定的文檔中查詢醫療知識

**Features**:
- Ingest medical documents in multiple formats (PDF, Word .docx, plain text)
  - 支持多種格式的醫療文檔攝入（PDF、Word .docx、純文本）
- Build semantic search index for medical terminology and procedures
  - 為醫療術語和程序構建語義搜索索引
- Answer patient questions with citations and confidence scores
  - 提供帶有引文和置信度分數的患者問題答案
- Respond within 3 seconds for real-time interaction
  - 在3秒內回應實時交互

**Implementation**:
- Vector database for semantic similarity search
- Hybrid search combining BM25 + semantic embedding
- Source document tracking and citation
- Confidence scoring based on retrieval similarity

---

### 1.2 Hermes Agent + Database Analysis | Hermes代理 + 數據庫分析

**Objective**: Provide Hermes agent with clinic HIS context for intelligent analysis and auto-skill generation

**目標**: 為Hermes代理提供診所HIS背景以進行智能分析和自動技能生成

**Features**:
- Connect to local HIS (Hospital Information System) database
  - 連接到本地醫院信息系統 (HIS) 數據庫
- Execute ad-hoc analytical queries on patient/clinic data
  - 對患者/診所數據執行即席分析查詢
- Agent learns clinic-specific patterns from successful queries
  - 代理從成功的查詢中學習診所特定的模式
- Auto-generate CLI tools and skills from learned patterns
  - 從學習到的模式自動生成CLI工具和技能
- Expose custom commands for clinic staff use
  - 為診所員工公開自定義命令

**Implementation**:
- Database abstraction layer for HIS connectivity
- Query execution with result caching
- Pattern recognition system for skill discovery
- Auto-tool generation from query patterns
- Metrics tracking for skill adoption

---

### 1.3 Multi-Channel Patient Communication | 多渠道患者通信

**Objective**: Unify patient communication across LINE and web platforms with single staff interface

**目標**: 通過單一員工界面統一LINE和網絡平台上的患者通信

**Features**:
- LINE bot integration for patient inquiries
  - LINE機器人集成用於患者查詢
- doctor-toolbox.com/chats integration for web-based chat
  - doctor-toolbox.com/chats集成用於基於Web的聊天
- Unified inbox for clinic staff (manage all channels from one interface)
  - 診所員工的統一收件箱（從一個界面管理所有渠道）
- Conversation history per patient with context retention
  - 每個患者的對話歷史，保留上下文
- Message routing to RAG chatbot and manual escalation
  - 消息路由到RAG聊天機器人和手動升級

**Implementation**:
- Message queue system for unified inbox
- Channel abstraction layer (LINE, web chat, etc.)
- Session management per patient
- Auto-routing based on message type (medical query vs escalation)
- Conversation persistence layer

---

### 1.4 Local LLM Infrastructure | 本地LLM基礎設施

**Objective**: Serve large language models locally on 2080Ti GPU without cloud API dependency

**目標**: 在2080Ti GPU上本地服務大型語言模型，無需雲API依賴

**Features**:
- llama.cpp for optimized local inference
  - 使用llama.cpp進行優化的本地推理
- Support for Qwen 3.6 and Gemma 4 models
  - 支持Qwen 3.6和Gemma 4模型
- VRAM optimization for 22GB GPU (streaming output, quantization)
  - 針對22GB GPU的VRAM優化（流式輸出、量化）
- GPU memory monitoring and overflow prevention
  - GPU內存監控和溢出防止
- Inference API for RAG chatbot and agent integration
  - 用於RAG聊天機器人和代理集成的推理API

**Implementation**:
- llama.cpp server with REST/gRPC API
- Model loading and caching strategy
- VRAM profiling and dynamic batching
- Memory monitoring with alerts
- Fallback inference on CPU if needed

---

### 1.5 Web Forms & Data Entry | 網絡表格和數據輸入

**Objective**: Enable clinic staff and patients to enter data directly into HIS and CRM systems

**目標**: 使診所員工和患者能夠將數據直接輸入到HIS和CRM系統

**Features**:
- Patient intake web forms with validation
  - 具有驗證的患者入院網絡表格
- Auto-population of HIS database from form submissions
  - 從表單提交中自動填充HIS數據庫
- Patient record dashboard for history and follow-up
  - 用於歷史和後續跟進的患者記錄儀表板
- Integration with doctor-toolbox.com CRM
  - 與doctor-toolbox.com CRM集成
- Form submission audit trail
  - 表單提交審計跟踪

**Implementation**:
- Web form builder with validation rules
- Auto-mapping to HIS schema
- ORM layer for database operations
- CRM API integration
- Submission history and audit logging

---

### 1.6 Hermes Auto-Skills & CLI | Hermes自動技能和CLI

**Objective**: Enable clinic to grow tooling organically from successful agent patterns

**目標**: 使診所能夠從成功的代理模式中有機地發展工具

**Features**:
- Auto-skill creation from successful agent patterns
  - 從成功的代理模式中自動創建技能
- Dynamic skill discovery and loading
  - 動態技能發現和加載
- CLI command generation from skills
  - 從技能生成CLI命令
- Skill adoption metrics and reporting
  - 技能采用指標和報告
- Versioning and skill management
  - 版本控制和技能管理

**Implementation**:
- Pattern detection system for successful queries
- Skill definition language (YAML/JSON)
- Dynamic CLI command registration
- Skill execution engine
- Metrics collection and dashboard

---

## 2. Architecture Overview | 架構概述

```
┌─────────────────────────────────────────────────────────────┐
│                    Patient/Staff Interfaces                 │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ LINE Bot     │ Web Chat     │ Web Forms    │ CLI Commands   │
│ (LINE API)   │ (doctor-    │ (Django/    │ (Hermes CLI)   │
│              │ toolbox)    │ Flask)      │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
                             │
┌──────────────────────────────────────────────────────────────┐
│              Unified Message Queue & Routing                │
│          (Message routing, session management)              │
└──────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌───────▼──────────┐  ┌─────▼──────────┐
│ RAG Chatbot    │  │ Hermes Agent     │  │ Manual Routing │
│ - Vector DB    │  │ - HIS Context    │  │ (escalation)   │
│ - Semantic     │  │ - Query Engine   │  │                │
│   Search       │  │ - Skill Gen      │  │                │
└───────┬────────┘  └───────┬──────────┘  └─────┬──────────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │
┌──────────────────────────────────────────────────────────────┐
│            Local LLM Inference (llama.cpp)                  │
│        ┌──────────────────────────────────┐                 │
│        │  Qwen 3.6 / Gemma 4 on 2080Ti    │                 │
│        │  (22GB VRAM, ~200ms latency)     │                 │
│        └──────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼─────────┐                 ┌──────────▼──────┐
│ Local HIS DB    │                 │ Vector DB       │
│ (MySQL/         │                 │ (Chroma/FAISS)  │
│  PostgreSQL)    │                 │                 │
└─────────────────┘                 └─────────────────┘
        │
        └──────────────────────────────┐
                                       │
                            ┌──────────▼──────┐
                            │ Cloud Sync      │
                            │ (Phase 5)       │
                            │ doctor-toolbox  │
                            └─────────────────┘
```

---

## 3. Technology Stack | 技術棧

### LLM & Inference | LLM和推理
- **Engine**: llama.cpp (local inference optimization)
- **Models**: Qwen 3.6 (primary), Gemma 4 (future)
- **Hardware**: NVIDIA 2080Ti (22GB VRAM)
- **GPU Optimization**: Quantization (Q8_0, Q4_K_M), streaming output

### Vector & Semantic Search | 向量和語義搜索
- **Vector DB**: Chroma or FAISS (local embedding storage)
- **Embeddings**: HuggingFace sentence transformers (local)
- **Hybrid Search**: BM25 (keyword) + semantic (vector similarity)

### Backend | 後端
- **Framework**: Flask or FastAPI (Python)
- **Database**: PostgreSQL or MySQL (HIS connectivity)
- **Message Queue**: Redis (conversation history, message buffering)
- **Hermes Integration**: Hermes agent module (existing codebase)

### Frontend | 前端
- **Web Forms**: Django/Flask + HTML/CSS/JavaScript
- **Dashboard**: React or Vue.js (patient records, metrics)
- **Admin CLI**: Hermes CLI (Python/Bash)

### Integration | 集成
- **LINE API**: Official LINE Bot SDK (Python/Node.js)
- **doctor-toolbox.com**: REST API integration (cloud sync, CRM)
- **HIS Database**: ODBC/native DB driver (clinic-specific)

---

## 4. Implementation Phases | 實施階段

### Phase 1: Foundation (Weeks 1-3) | 基礎階段（第1-3週）
**Goal**: Local LLM and RAG chatbot operational

**目標**: 本地LLM和RAG聊天機器人可運行

**Deliverables**:
- llama.cpp setup guide for 2080Ti
- Qwen 3.6 model serving at <200ms latency
- RAG pipeline: document ingestion → indexing → semantic search
- Confidence scoring and citation system
- API endpoint for RAG queries

**關鍵交付成果**:
- llama.cpp 2080Ti設置指南
- Qwen 3.6模型以<200ms延遲提供服務
- RAG管道：文檔攝入→索引→語義搜索
- 置信度評分和引文系統
- RAG查詢的API端點

---

### Phase 2: Clinic Integration (Weeks 4-6) | 診所集成（第4-6週）
**Goal**: HIS database connectivity and LINE patient communication

**目標**: HIS數據庫連接和LINE患者通信

**Deliverables**:
- HIS database connection and query execution
- Query result caching for performance
- LINE bot integration and message routing
- Conversation history per patient
- Message buffering and error handling

**關鍵交付成果**:
- HIS數據庫連接和查詢執行
- 查詢結果緩存以提高性能
- LINE機器人集成和消息路由
- 每個患者的對話歷史
- 消息緩衝和錯誤處理

---

### Phase 3: Patient Engagement (Weeks 7-9) | 患者參與（第7-9週）
**Goal**: Web forms, dashboard, and multi-channel communication

**目標**: 網絡表格、儀表板和多渠道通信

**Deliverables**:
- Patient intake web forms with validation
- Auto-population of HIS from form submissions
- Patient record dashboard
- doctor-toolbox.com/chats integration
- Unified staff inbox (LINE + web chat)

**關鍵交付成果**:
- 具有驗證的患者入院網絡表格
- 從表單提交中自動填充HIS
- 患者記錄儀表板
- doctor-toolbox.com/chats集成
- 統一員工收件箱（LINE + 網絡聊天）

---

### Phase 4: Intelligence Growth (Weeks 10-12) | 智能增長（第10-12週）
**Goal**: Hermes agent integration and auto-skills

**目標**: Hermes代理集成和自動技能

**Deliverables**:
- Hermes agent initialization with HIS context
- Pattern learning from successful queries
- Auto-skill creation and CLI command generation
- Skill discovery and dynamic loading
- Adoption metrics and reporting

**關鍵交付成果**:
- Hermes代理初始化和HIS背景
- 從成功查詢中學習模式
- 自動技能創建和CLI命令生成
- 技能發現和動態加載
- 采用指標和報告

---

### Phase 5: Enterprise Features (Weeks 13-15) | 企業功能（第13-15週）
**Goal**: Cloud sync and production optimization

**目標**: 雲同步和生產優化

**Deliverables**:
- Bidirectional sync with doctor-toolbox.com
- Patient data and analytics in cloud dashboard
- Performance optimization and monitoring
- Production hardening and security
- Clinic staff training and documentation

**關鍵交付成果**:
- 與doctor-toolbox.com雙向同步
- 患者數據和雲儀表板中的分析
- 性能優化和監控
- 生產強化和安全性
- 診所員工培訓和文檔

---

## 5. Success Metrics | 成功指標

| Metric | Target | Rationale |
|--------|--------|-----------|
| RAG response time | <3 seconds | Patient query satisfaction |
| RAG relevance | 80%+ | Medical query accuracy |
| Hermes query latency | <5 seconds on 100K+ records | HIS analysis speed |
| Auto-answered questions | 90%+ without escalation | Reduce staff burden |
| GPU memory | No overflow at 22GB | System stability |
| Auto-skills created | 5+ in first month | Clinic growth metric |

---

## 6. Risks & Mitigation | 風險和緩解

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| GPU memory overflow | Medium | Stress testing, streaming fallback, dynamic batching |
| RAG relevance too low | Medium | Hybrid search, fine-tuning, user feedback |
| HIS connectivity fragility | Medium | Error handling, query caching, clinic IT coordination |
| Skill learning curve steep | Low | Clear documentation, in-app tutorials |
| Cloud sync data conflicts | Low | Conflict resolution algorithm, audit trail |

---

## 7. Dependencies & Prerequisites | 依賴關係和先決條件

**Hardware**: NVIDIA 2080Ti with 22GB VRAM  
**Software**: Linux server (Ubuntu 20.04+), Python 3.9+, CUDA 11.8+  
**Data**: Sample medical documents (PDF, Word) for RAG indexing  
**Access**: HIS database connection (clinic IT coordination)  
**Accounts**: LINE official account, doctor-toolbox.com developer account  

---

## 8. Next Steps | 後續步驟

1. **Approve roadmap** — Review 5-phase plan and timeline
   - 批准路線圖 - 審查5階段計劃和時間表

2. **Prepare Phase 1** — Gather medical documents, verify GPU setup
   - 準備第1階段 - 收集醫療文檔、驗證GPU設置

3. **Start Phase 1** — Run `/gsd-plan-phase 1` for detailed breakdown
   - 開始第1階段 - 運行`/gsd-plan-phase 1`進行詳細分解

4. **Track progress** — Use git commits and phase transitions for continuity
   - 跟蹤進度 - 使用git提交和階段過渡以保持連續性

5. **Validate completion** — Each phase must achieve 100% of success criteria
   - 驗證完成 - 每個階段必須達到成功標準的100%

---

## 9. Strategic Advice & Plan Improvements | 戰略建議與計畫改進

Based on a deep review of the workspace and current architecture, the following recommendations are provided to enhance the execution plan:
基於對工作區和當前架構的深入研究，提出以下建議以完善執行計畫：

### 9.1 Clarify the Role of `hermes-desktop` | 明確 `hermes-desktop` 的作用
**Observation (觀察)**: The workspace contains a robust `hermes-desktop` Electron/Vite application, yet the plan primarily references "Web Forms" and "doctor-toolbox.com/chats" for the staff interface.
**Advice (建議)**: Explicitly integrate `hermes-desktop` into the "Architecture Overview" and Phase 3. It should be positioned as the primary local dashboard and unified staff inbox for clinic operations, replacing or augmenting the web-based CRM for on-premises use.

### 9.2 Integrate `AstrBot` into the Communication Layer | 將 `AstrBot` 整合到通信層
**Observation (觀察)**: The `AstrBot` framework is present in the repository but not mentioned in the plan.
**Advice (建議)**: Update Phase 2 and the Architecture Overview to specify `AstrBot` as the message routing and LINE bot integration engine. Clarify how `AstrBot` will interface with the RAG pipeline and Hermes agent.

### 9.3 Secure HIS Database Access (Read-Only Replica) | 保護 HIS 數據庫訪問 (唯讀副本)
**Observation (觀察)**: Phase 2 and Phase 4 involve the Hermes agent querying the HIS database.
**Advice (建議)**: For risk mitigation, explicitly require the use of a **Read-Only Replica** or strictly permissioned database user for the Hermes agent. This prevents any accidental data corruption or `DROP TABLE` scenarios during agent exploratory queries.

### 9.4 Refine Hardware Assumptions | 細化硬體假設
**Observation (觀察)**: The plan cites a 2080Ti with 22GB VRAM. Standard 2080Ti cards have 11GB VRAM (though 22GB modded versions exist).
**Advice (建議)**: If using an 11GB card, serving Qwen 3.6 might require heavier quantization (e.g., Q4_K_M) and strict context length limits. Add a specific sub-task in Phase 1 to benchmark the exact model size and context window against the physical VRAM available.

### 9.5 Phase Parallelization Strategy | 階段並行策略
**Observation (觀察)**: The 15-week timeline is sequential, but `.planning/STATE.md` notes potential parallelization.
**Advice (建議)**: Update the "Timeline" section to show that Phase 3 (Web Forms/Desktop) and Phase 4 (Hermes Agent) can be executed concurrently once Phase 2 (HIS Integration) is stable, potentially reducing the total timeline from 15 weeks to 10-12 weeks.

### 9.6 Dual Knowledge Base Architecture (Federated RAG) | 雙知識庫架構
**Observation (觀察)**: The system needs to handle both generic medical questions and clinic-specific operational questions.
**Advice (建議)**: Implement a strict structural separation of knowledge into two distinct domains:
1. **Medical Domain (通用醫療庫)**: `medical.db` + `general_medical` RAG collection. Contains common disease info, symptom checkers, and standard medical guidelines. This is static, highly reusable, and safe for all users.
2. **Clinical Domain (診所專屬庫)**: `clinic.db` + `clinic_specific` RAG collection. Contains operational data, clinic introductions, doctor schedules, and pricing. This is dynamic and strictly local to the clinic.
**Routing**: Introduce an intent classifier (or use Hermes Agent) to route user queries. "What is diabetes?" goes to the Medical Domain; "When can I see the doctor for diabetes?" queries Both. This prevents the LLM from hallucinating clinic services based on generic medical texts.

### 9.7 Phase 6: Security Hardening & Authentication | 第6階段：安全加固與身份驗證
**Observation (觀察)**: The recent code reviews in Phase 5 successfully addressed critical connection leaks and SQL injection risks. However, client-side authentication bypass vulnerabilities (e.g., CR-01) require architectural shifts to server-side session management, which were deferred.
**Advice (建議)**: Officially establish a **Phase 6** dedicated to security hardening. This phase should implement robust server-side session validation, role-based access control (RBAC), and conduct full security audits across all API endpoints (analytics, cloud_sync, staff_actions) to ensure enterprise-grade safety.
**建議**: 正式設立**第6階段**專注於安全加固。該階段應實施穩健的服務器端會話驗證、基於角色的訪問控制 (RBAC)，並對所有 API 端點（分析、雲端同步、員工操作）進行全面的安全審計，以確保企業級的安全性。

### 9.8 Continuous Testing & Integration Pipeline | 持續測試與整合流程
**Observation (觀察)**: As endpoints are updated with defensive patterns like `DBContext` and query optimizations, manual verification becomes a bottleneck and introduces regression risks.
**Advice (建議)**: Introduce automated test suites (e.g., using `pytest`) that cover all updated endpoints. Integrating a robust testing pipeline ensures that future database and API refactoring won't break existing functionalities, allowing for safer merges.
**建議**: 引入自動化測試套件（如使用 `pytest`）覆蓋所有已更新的端點。整合強大的測試流程可確保未來的數據庫和 API 重構不會破壞現有功能，讓代碼合併更安全。

### 9.9 Phase 7: System Setup & Ecosystem Integration | 第7階段：系統設定與生態系整合
**Goal**: Local server configuration UI, Chatbot platform, File Manager, and Automated CRM analysis
**目標**: 本地伺服器設定介面、聊天機器人平台、檔案管理器與自動化 CRM 分析

**Deliverables & Integrations (交付成果與整合方案)**:
1. **Setup Dashboard (系統初始設定中心)**: 建立一個集中式的設定頁面，允許管理員輸入診所名稱、API 金鑰及各項全域參數。
2. **AstrBot Integration (Robotbot 聊天機器人)**: 整合 `AstrBot` 作為診所對外 (如 LINE/Telegram) 的通訊機器人引擎，可透過 Flask 後端直接寫入設定檔與進行程序監控。
3. **FileBrowser Integration (檔案管理中心)**: 整合 `filebrowser` 並實作無縫登入 (SSO)，使診所員工可於網頁介面直接預覽與管理伺服器上的醫療文件。
4. **Hermes-Desktop (終端 CRM 分析應用)**: 部署客製化的 Hermes-Desktop client `.exe`，作為夜間自動化分析的 Worker。該客戶端將於夜間自動運行，針對 HIS 資料庫進行深入的 CRM 分析 (例如：病患回診追蹤、健康趨勢預測、名單自動標記等)。

---

## Document History | 文檔歷史

- **2026-05-06**: Initial project plan (user concept)
- **2026-05-06**: Expanded with full architecture, phases, tech stack, and bilingual documentation
- **2026-05-06**: Added Strategic Advice & Plan Improvements section based on deep workspace research.
- **2026-05-13**: Added strategic advice for Phase 6 (Security Hardening) and Testing Pipeline based on Phase 5 code review resolutions.
- **2026-05-13**: Added Phase 7 for System Setup and Ecosystem Integration (AstrBot, FileBrowser, Hermes-Desktop as Nightly CRM Analyzer).

---

*Last updated: 2026-05-13*  
*Project Status: Phase 5 completed, ready for testing and Phase 6 planning*  
*For detailed planning, see `.planning/PROJECT.md`, `.planning/ROADMAP.md`*
