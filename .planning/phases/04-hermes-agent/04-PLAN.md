# Phase 4: Intelligence Growth — Hermes Agent & Auto-Skills

## Phase Overview

**Objective:** Deploy Hermes agent for pattern learning and enable auto-skill generation for clinic staff.

**Success Criteria:**
1. Agent initializes with HIS context without errors (AGENT-01)
2. Agent identifies and learns clinic-specific query patterns (AGENT-02)
3. Custom CLI commands generated and accessible to clinic staff (AGENT-03)
4. Auto-skills dynamically loaded and trackable (SKILL-01, SKILL-02)
5. Skill adoption metrics tracked and reported (SKILL-03)
6. 5+ custom skills created within first 2 weeks of operation (success metric)

**Locked Decisions:** None — this is a new phase with flexible implementation.

---

## Implementation Structure

Phase 4 groups into **3 waves** with clear dependencies:

1. **Wave 1 (Foundation):** Hermes agent setup with HIS context
2. **Wave 2 (Pattern Learning):** Pattern learning system and CLI commands
3. **Wave 3 (Auto-Skills):** Auto-skill generation and metrics reporting

---

## Task Breakdown & Dependencies

### WAVE 1: Hermes Agent Setup with HIS Context

**Task 1.1: Integrate Hermes Agent with HIS Database**

- **Path:** `src/agent/hermes_core.py` (MODIFY)
- **Deliverable:**
  - Extend existing `HermesAgent` class to include full HIS context on initialization
  - Context includes: clinic_info, patient summary stats, recent appointments, staff list
  - Add `init_with_context()` method that loads clinic data on startup
  - Implement context refresh mechanism (manual trigger + auto-refresh every 30 minutes)
  - Add connection health check for HIS database
  - Per AGENT-01: "Spawn Hermes agent instance with local HIS context"

- **Acceptance Criteria:**
  - Agent loads without errors on startup
  - HIS context available in all chat sessions
  - Context refresh works without interruption
  - Test: `python -c "from src.agent.hermes_core import get_hermes_agent; a = get_hermes_agent(); print('OK')"`

- **Owner:** Agent layer
- **Dependency:** None (foundational)
- **Implements:** AGENT-01

---

**Task 1.2: Create Hermes CLI Entry Point for Clinic Staff**

- **Path:** `scripts/hermes_cli.py` (NEW)
- **Deliverable:**
  - Flask CLI entry point that wraps Hermes agent for clinic staff
  - Command structure:
    - `hermes-cli chat` — Interactive chat mode
    - `hermes-cli query <question>` — Single query mode
    - `hermes-cli status` — Show agent health and context status
    - `hermes-cli context refresh` — Force context refresh
  - Integration with existing `hermes-agent/hermes_cli/main.py` (reuse or extend)
  - Bootstrap 5 styled CLI output (colored prompts, tables for status)
  - Per AGENT-03: "Agent exposes custom CLI commands for clinic staff"

- **Acceptance Criteria:**
  - CLI runs without errors
  - All commands documented and accessible
  - Status shows HIS connection health
  - Test: `python scripts/hermes_cli.py status` shows clinic info

- **Owner:** CLI layer
- **Dependency:** Task 1.1 (agent initialization)
- **Implements:** AGENT-01, AGENT-03

---

### WAVE 2: Pattern Learning and CLI Commands

**Task 2.1: Implement Advanced Pattern Learning System**

- **Path:** `src/agent/pattern_learner.py` (ENHANCE)
- **Deliverable:**
  - Enhance existing `PatternLearner` class with semantic pattern detection
  - Add embedding-based similarity detection (use existing RAG embeddings if available, or simple TF-IDF fallback)
  - Implement pattern threshold configuration (default: 3 occurrences in 7 days)
  - Add pattern categorization: "patient_query", "staff_task", "medical_info", "clinic_operation"
  - Store patterns in SQLite (`clinic.db.patterns` table)
  - Pattern candidate generation with confidence score
  - Per AGENT-02: "Agent learns clinic-specific patterns from queries"

- **Acceptance Criteria:**
  - Patterns detected from conversation history
  - Candidate skills generated automatically
  - Pattern categories assigned correctly
  - Test: Query patterns appear in database after 3+ similar queries

- **Owner:** Agent layer
- **Dependency:** Task 1.1 (Hermes agent with context)
- **Implements:** AGENT-02

---

**Task 2.2: Create Staff CLI Commands for Pattern Management**

- **Path:** `scripts/hermes_cli.py` (EXTEND)
- **Deliverable:**
  - Add CLI commands for staff:
    - `hermes-cli patterns list` — Show learned patterns
    - `hermes-cli patterns approve <pattern_id>` — Approve candidate to skill
    - `hermes-cli patterns reject <pattern_id>` — Reject candidate
    - `hermes-cli patterns stats` — Show pattern statistics
  - Bootstrap 5 styled table output for pattern list
  - Confirmation prompts for approve/reject actions
  - Per AGENT-03: "Agent exposes custom CLI commands for clinic staff"

- **Acceptance Criteria:**
  - Staff can view all patterns
  - Staff can approve/reject pattern candidates
  - Statistics display accurate counts
  - Test: `python scripts/hermes_cli.py patterns list` shows patterns

- **Owner:** CLI layer
- **Dependency:** Task 2.1 (pattern learning)
- **Implements:** AGENT-02, AGENT-03

---

### WAVE 3: Auto-Skill Generation and Metrics

**Task 3.1: Implement Auto-Skill Generation from Patterns**

- **Path:** `src/skills/skill_generator.py` (ENHANCE)
- **Deliverable:**
  - Enhance existing `SkillGenerator` to convert approved patterns to skills
  - Use LLM to generate Python script for each pattern
  - Script template includes:
    - `run(**kwargs)` function
    - HIS database query capability
    - Error handling and logging
    - Return format: `{"status": "success/error", "data": ...}`
  - Save generated skills to `src/skills/auto_skills/` directory
  - Auto-register skills in database (`auto_skills` table)
  - Per SKILL-01: "Auto-skill creation from successful agent patterns"

- **Acceptance Criteria:**
  - Approved patterns generate valid Python scripts
  - Scripts execute without errors
  - Skills registered in database
  - Test: Approve pattern → skill generated → execute skill works

- **Owner:** Skills layer
- **Dependency:** Task 2.2 (pattern approval workflow)
- **Implements:** SKILL-01

---

**Task 3.2: Implement Skill Discovery and Dynamic Loading**

- **Path:** `src/skills/skill_manager.py` (ENHANCE)
- **Deliverable:**
  - Enhance existing `SkillManager` with discovery capabilities
  - Auto-discover skills from `src/skills/auto_skills/` directory
  - Dynamic skill loading without restart
  - Skill metadata: name, description, command_pattern, created_at, usage_count
  - Skill enable/disable capability
  - Per SKILL-02: "Skill discovery and dynamic loading"

- **Acceptance Criteria:**
  - All skills in auto_skills directory discoverable
  - Skills can be enabled/disabled at runtime
  - Dynamic loading doesn't interrupt agent operation
  - Test: Add new skill file → it appears in list automatically

- **Owner:** Skills layer
- **Dependency:** Task 3.1 (skill generation)
- **Implements:** SKILL-02

---

**Task 3.3: Implement Skill Adoption Metrics and Growth Reporting**

- **Path:** `src/skills/metrics.py` (NEW)
- **Deliverable:**
  - Metrics tracking table in clinic.db (`skill_metrics` table)
  - Track per skill: execution_count, success_count, failure_count, avg_execution_time_ms, last_executed_at
  - Growth report generation:
    - Daily/weekly/monthly skill usage statistics
    - Top performing skills
    - Failed skill analysis
  - CLI command for metrics: `hermes-cli skills metrics`
  - Bootstrap 5 styled dashboard output (tables, charts via ASCII)
  - Per SKILL-03: "Skill adoption metrics and growth reporting"

- **Acceptance Criteria:**
  - All skill executions logged with metrics
  - Metrics queryable and accurate
  - Growth report generates correctly
  - Test: Execute skill → metrics updated → metrics command shows data

- **Owner:** Metrics layer
- **Dependency:** Task 3.2 (skill execution)
- **Implements:** SKILL-03

---

**Task 3.4: Create CLI Commands for Skill Management**

- **Path:** `scripts/hermes_cli.py` (EXTEND)
- **Deliverable:**
  - Add CLI commands:
    - `hermes-cli skills list` — List all registered skills
    - `hermes-cli skills run <skill_id> [args]` — Execute a skill
    - `hermes-cli skills enable <skill_id>` — Enable disabled skill
    - `hermes-cli skills disable <skill_id>` — Disable active skill
    - `hermes-cli skills metrics` — Show adoption metrics
    - `hermes-cli skills create --pattern <pattern_id>` — Create skill from pattern
  - Help text for each command
  - Per AGENT-03, SKILL-02: CLI commands for skill management

- **Acceptance Criteria:**
  - All skill management commands work
  - Help text displays correctly
  - Execution with arguments works
  - Test: Full skill lifecycle (create, list, run, metrics)

- **Owner:** CLI layer
- **Dependency:** Task 3.1, 3.2, 3.3 (all skills components)
- **Implements:** AGENT-03, SKILL-01, SKILL-02, SKILL-03

---

## Dependency Graph

```
Wave 1 (Foundation):
  Task 1.1 (Hermes + HIS) — no dependencies
  Task 1.2 (CLI entry point) → depends on Task 1.1

Wave 2 (Pattern Learning):
  Task 2.1 (Pattern learning) → depends on Task 1.1
  Task 2.2 (Pattern CLI) → depends on Task 2.1

Wave 3 (Auto-Skills):
  Task 3.1 (Skill generation) → depends on Task 2.2
  Task 3.2 (Skill discovery) → depends on Task 3.1
  Task 3.3 (Metrics) → depends on Task 3.2
  Task 3.4 (Skill CLI) → depends on Task 3.1, 3.2, 3.3
```

**Critical Path:** Task 1.1 → Task 2.1 → Task 2.2 → Task 3.1 → Task 3.2 → Task 3.3 → Task 3.4

**Parallelization Opportunities:**
- Task 1.1 and Task 1.2 can be developed in parallel after design review
- Task 3.2 can start after Task 3.1 completes (skill generation produces skills to discover)

---

## Risk & Mitigation

| Risk | Impact | Mitigation | Owner |
|------|--------|-------------|-------|
| LLM-based skill generation produces broken code | Skills fail at runtime | Validate generated code with syntax check before registration; have fallback manual creation | Skills layer |
| Pattern detection too aggressive | Too many false positives | Require 3+ occurrences before suggesting; staff approval gate filters noise | Agent layer |
| HIS context stale | Agent provides outdated info | Auto-refresh every 30 min; manual refresh command available | Agent layer |
| Skill execution crashes agent | Service interruption | Skill execution in isolated subprocess; timeout after 30s | Skills layer |
| Metrics database grows unbounded | Performance degradation | Auto-purge metrics older than 90 days; aggregate to monthly | Metrics layer |
| CLI too complex for non-technical staff | Low adoption | Simple commands with defaults; built-in help; Bootstrap 5 styled output | CLI layer |

---

## Rollout Strategy

### Phase 4 Deployment Stages

**Stage 1: Hermes Agent Foundation (Wave 1)**
- Deploy Task 1.1: Hermes agent with HIS context
- Deploy Task 1.2: CLI entry point
- Test: Agent starts with context, CLI commands work
- Milestone: Staff can chat with agent and see clinic context

**Stage 2: Pattern Learning (Wave 2)**
- Deploy Task 2.1: Pattern learning system
- Deploy Task 2.2: Pattern CLI commands
- Test: Patterns detected from conversation history
- Milestone: Agent learns patterns automatically

**Stage 3: Auto-Skills (Wave 3)**
- Deploy Task 3.1: Skill generation
- Deploy Task 3.2: Skill discovery
- Deploy Task 3.3: Metrics tracking
- Deploy Task 3.4: Skill CLI commands
- Test: Full skill lifecycle works
- Milestone: 5+ custom skills created within 2 weeks

**Stage 4: Production Verification**
- Run integration tests
- Staff training on CLI commands
- Monitor metrics for 2 weeks
- Verify 5+ skills created target

**Rollback Plan:**
- If critical bug: Disable auto-skill creation, keep manual pattern approval
- If agent unstable: Roll back to Wave 1 only (chat without patterns)
- Restore clinic.db from pre-migration backup if needed

---

## Success Metrics

### Functional Success

1. **Agent Initialization (AGENT-01)**
   - Acceptance: Agent starts with HIS context loaded
   - Measurement: `hermes-cli status` shows clinic info
   - Baseline: 100% successful initialization

2. **Pattern Learning (AGENT-02)**
   - Acceptance: Patterns detected from 3+ similar queries
   - Measurement: Patterns appear in database
   - Baseline: 5+ patterns detected in first week

3. **CLI Commands (AGENT-03)**
   - Acceptance: Staff can execute all commands
   - Measurement: All commands documented and tested
   - Baseline: 8+ CLI commands available

4. **Auto-Skill Creation (SKILL-01)**
   - Acceptance: Approved patterns generate executable skills
   - Measurement: Skills in auto_skills directory
   - Baseline: 5+ skills in first 2 weeks

5. **Skill Discovery (SKILL-02)**
   - Acceptance: New skills auto-discovered
   - Measurement: Skills appear in list without restart
   - Baseline: 100% discovery rate

6. **Metrics Reporting (SKILL-03)**
   - Acceptance: All executions logged with metrics
   - Measurement: Growth report accurate
   - Baseline: 100% execution logging

### Performance Baselines

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Agent initialization | <5s | Time from CLI start to ready |
| Context refresh | <10s | Time for manual refresh command |
| Pattern detection | <1s | Per query processing time |
| Skill execution | <5s | Average execution time |
| Metrics query | <500ms | Report generation time |

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Agent Core | Python + llama.cpp client | Existing src/agent/hermes_core.py |
| Pattern Learning | TF-IDF or embedding similarity | Reuse existing RAG infrastructure |
| Skill Generation | LLM-based code generation | Existing src/skills/skill_generator.py |
| Skill Storage | SQLite (clinic.db) | Existing database |
| CLI | Click or argparse | Simple, no new dependencies |
| Frontend (CLI) | Bootstrap 5 styled output | Consistent with web templates |
| Metrics | SQLite + aggregation queries | Existing pattern |

---

## File Checklist

**New Files (Phase 4):**
- `scripts/hermes_cli.py` — NEW (CLI entry point)
- `src/skills/metrics.py` — NEW (metrics tracking)
- `src/agent/context_manager.py` — NEW (HIS context management)
- `src/templates/hermes_cli_status.html` — NEW (CLI status template, if needed)

**Modified Files (Phase 4):**
- `src/agent/hermes_core.py` — MODIFY (add context loading)
- `src/agent/pattern_learner.py` — MODIFY (enhance pattern detection)
- `src/skills/skill_manager.py` — MODIFY (add discovery)
- `src/skills/skill_generator.py` — MODIFY (enhance generation)

**Database Changes:**
- Add `patterns` table for pattern storage
- Add `skill_metrics` table (may already exist from skill_manager.py)
- Add `auto_skills` table columns if needed

---

## Implementation Notes

### Reusing Phase 1-3 Assets

Phase 4 builds on existing infrastructure:

- **RAG System (Phase 1):** Use embeddings for semantic pattern matching
- **HIS Connection (Phase 2):** Reuse `HISConnection` class for context
- **Conversation History (Phase 2):** Use `conversation_manager` for pattern detection
- **Staff Communication (Phase 3):** Pattern learning monitors staff conversations

### Hermes Agent Integration

The `hermes-agent/` directory contains the full Hermes CLI framework. For this phase:
- Use the Drtoolbox-specific `HermesAgent` class (src/agent/hermes_core.py)
- Extend with clinic-specific context and commands
- Reuse Hermes tools and patterns where applicable

---

## Success Verification Checklist

Before Phase 4 is considered "done", verify:

- [ ] Hermes agent initializes with HIS context (Task 1.1)
- [ ] CLI entry point works for clinic staff (Task 1.2)
- [ ] Pattern learning detects clinic-specific patterns (Task 2.1)
- [ ] Pattern CLI commands available (Task 2.2)
- [ ] Auto-skill generation works (Task 3.1)
- [ ] Skill discovery dynamic (Task 3.2)
- [ ] Metrics tracking operational (Task 3.3)
- [ ] Skill CLI commands complete (Task 3.4)
- [ ] 5+ custom skills created within 2 weeks (success metric)
- [ ] Staff trained on CLI usage
- [ ] Performance baselines met

---

## Next Steps (Phase 5)

Phase 4 unlocks Phase 5 (Enterprise Features):

1. **Cloud Sync:** Bidirectional sync with doctor-toolbox.com
2. **Advanced Metrics:** Charts, dashboards, exports
3. **Multi-language Support:** Add English/Simplified Chinese
4. **Voice Integration:** Voice input/output for Hermes

---

*Plan created: 2026-05-12*  
*Phase: 04-hermes-agent*  
*Waves: 3*  
*Tasks: 8*