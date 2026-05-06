# DrtoolboxLocalServer — Project Memory & State

## Initialization Context

**Date**: 2026-05-06  
**Status**: Initialized, ready for Phase 1 execution  
**Mode**: YOLO (coarse-grained, parallel execution)  

## Project Discovery Synthesis

### User Intent
Clinic intelligence platform enabling local-first medical decision support without cloud dependency. User is building on 15+ weeks of Hermes agent work and has clear vision: privacy-first local deployment with optional cloud sync, RAG over medical docs, local LLM on 2080Ti GPU, Hermes agent auto-skills for clinic growth.

### Domain Understanding
- **Medical Context**: Clinic needs intelligent patient communication (LINE), medical knowledge access (RAG), and data analysis (Hermes + HIS)
- **Technical Constraints**: 2080Ti GPU (22GB VRAM) limits LLM choice; llama.cpp preferred for inference control
- **Growth Model**: Auto-skills enable platform to adapt to clinic-specific patterns; not one-size-fits-all

### Key Decisions Rationale
1. **Local-first LLM**: Privacy non-negotiable for clinic data; offline operation prevents external API dependency
2. **Hermes agent**: User has 15+ weeks of Hermes work; platform grows with clinic patterns
3. **Multi-channel communication**: Clinic staff context-switch cost high; unified inbox essential
4. **RAG on medical documents**: Clinic-specific knowledge improves trust and relevance vs generic LLMs
5. **HIS integration**: Clinic already has systems; bridge them rather than replace

---

## Phase 1 Dependencies & Preparation

### Required Before Phase 1 Start
- [ ] llama.cpp installation guide for 2080Ti (VRAM optimization)
- [ ] Qwen 3.6 model availability verified (check if already downloaded)
- [ ] Sample medical documents ready for RAG indexing
- [ ] Inference API design (REST vs gRPC decision)
- [ ] Vector DB selection (Chroma, Pinecone, FAISS, etc.)

### Known Unknowns for Phase 1
- **Model latency baseline**: Unknown if Qwen 3.6 achieves <200ms at 22GB VRAM; may need quantization/pruning
- **RAG vector quality**: Semantic search quality on medical text not yet validated
- **GPU memory profile**: Actual peak VRAM under load unknown; may trigger overflow
- **Clinic document format**: How many Word docs vs PDFs? OCR needed for scanned docs?

### Phase 1 Success Gate
- Qwen 3.6 inference <200ms latency, <20GB VRAM
- RAG similarity search working on >100 medical documents
- No OOM errors under 1hr continuous operation

---

## Architecture Decisions Logged

### Decision: Local-First Deployment
- **Date**: 2026-05-06 (initialization)
- **Status**: Confirmed
- **Rationale**: Privacy, offline operation, cost control
- **Implication**: Cloud sync in Phase 5, not earlier

### Decision: Hermes Agent Integration  
- **Date**: 2026-05-06 (initialization)
- **Status**: Confirmed
- **Rationale**: Existing 15+ weeks of Hermes work; auto-skills enable clinic growth
- **Implication**: Phase 4 dependent on Hermes codebase stability

### Decision: RAG-First, Agent-Second
- **Date**: 2026-05-06 (initialization)
- **Status**: Confirmed
- **Rationale**: RAG provides immediate patient value; agent learns over time
- **Implication**: Phase 1-3 may run in parallel with Phase 4 agent integration

### Decision: 5-Phase Sequential Delivery
- **Date**: 2026-05-06 (initialization)
- **Status**: Confirmed
- **Rationale**: Coarse-grained phases reduce ceremony; each phase stands alone; parallel Phase 4 possible
- **Implication**: Team can pivot between phases based on dependency completion

---

## Team & Communication

### Key Stakeholders
- **Clinic Owner/Operator**: Primary user; drives requirement prioritization
- **Development Team**: Will execute roadmap phases
- **Hermes Maintainer**: Critical for Phase 4 integration

### Communication Plan
- Phase entry: `/gsd-discuss-phase N` for team alignment
- Phase exit: `/gsd-transition` to validate completion
- Milestone completions: `/gsd-complete-milestone` for cross-cutting updates

---

## Risk Register

### High-Impact, Medium-Probability Risks

**Risk 1: GPU Memory Overflow Under Load**
- **Impact**: Production crash, data loss if inference not graceful
- **Probability**: Medium (depends on batch size, context length)
- **Mitigation**: Phase 1 stress testing, streaming output fallback, dynamic batch sizing
- **Owner**: Phase 1 lead

**Risk 2: RAG Relevance Lower Than Expected**
- **Impact**: Patient frustration, low adoption
- **Probability**: Medium (medical text is complex; semantic search may struggle)
- **Mitigation**: Hybrid search (BM25 + semantic), fine-tuning on medical corpus, user feedback loop
- **Owner**: Phase 1 lead, user feedback

**Risk 3: HIS Database Connectivity Fragility**
- **Impact**: Hermes agent failures, clinic operations blocked
- **Probability**: Medium (clinic IT infrastructure often legacy/unstable)
- **Mitigation**: Comprehensive error handling, query caching, fallback mode, clinic IT coordination
- **Owner**: Phase 2 lead, clinic IT

**Risk 4: Skill Learning Curve Too Steep**
- **Impact**: Clinic staff overwhelmed, low adoption of auto-skills
- **Probability**: Low (good UX design can mitigate)
- **Mitigation**: Clear CLI documentation, in-app tutorials, skill discovery UI, usage metrics
- **Owner**: Phase 4 lead, UX design

### Low-Probability, Medium-Impact Risks

**Risk 5: Cloud Sync Data Conflicts**
- **Impact**: Data inconsistency, trust erosion
- **Probability**: Low (conflict resolution strategy important)
- **Mitigation**: Conflict resolution algorithm, audit trail, manual conflict resolution UI
- **Owner**: Phase 5 lead

**Risk 6: Regulatory/Compliance Blockers**
- **Impact**: Deployment halted, re-architecture required
- **Probability**: Low (clinic aware of HIPAA/GDPR but not primary driver)
- **Mitigation**: Early clinic IT/legal review, privacy-first design already in place
- **Owner**: Project sponsor, clinic IT

---

## Dependency Map

```
Phase 1: LLM + RAG
    ↓
Phase 2: HIS + LINE
    ↓
Phase 3: Web Forms + Multi-Channel (can parallelize with Phase 4)
    ↓
Phase 4: Hermes Agent (can start after Phase 2 HIS integration)
    ↓
Phase 5: Cloud Sync
```

### Can Parallelize
- **Phases 3 & 4**: Web forms development independent of Hermes agent integration
- **Phases 1 & 2**: With proper API contracts, can start Phase 2 LINE bot while Phase 1 LLM/RAG optimizing

---

## Success Criteria — Project-Level

✓ **Phase-Level Success**: Each phase achieves 100% of success criteria before entry to next phase  
✓ **Requirement Coverage**: 100% of v1 requirements delivered (27 requirements mapped to phases 1-5)  
✓ **Business Metrics**: All 5 success metrics achieved by end of Phase 5  
✓ **Production Readiness**: Zero critical bugs, comprehensive monitoring, clinic staff trained  

---

## Continuation Protocol

When continuing from this initialization state:

1. **Start Phase 1**: `cd .planning && cat ROADMAP.md | grep "Phase 1" -A 20` for context
2. **Track Progress**: Use `/gsd-plan-phase 1` for detailed Phase 1 breakdown
3. **Log Discoveries**: Use `/gsd-discover` or git commit messages to capture learnings
4. **Update STATE**: After each phase transition, update Risk Register and Known Unknowns
5. **Validate Completion**: Before moving to next phase, `/gsd-transition` for gate review

---

## Files in This Initiative

```
.planning/
├── config.json          ← Workflow preferences (yolo, coarse, parallel)
├── PROJECT.md           ← Project vision, decisions, context
├── REQUIREMENTS.md      ← v1 requirements, traceability
├── ROADMAP.md           ← 5-phase execution plan, timeline
└── STATE.md             ← This file: memory, risks, dependencies
```

---

*Last updated: 2026-05-06 after project initialization*  
*Next step: Run `/gsd-plan-phase 1` to begin Phase 1 execution planning*
