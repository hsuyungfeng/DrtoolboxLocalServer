-- patient_conversations_table.sql
-- Conversation history for patient-bot interactions
-- Created: 2026-05-08 (Task 9 - Wave 3)
-- TTL: 7 days per decision D-06

-- ============================================================================
-- Conversation History Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    message_id TEXT UNIQUE,
    sender TEXT NOT NULL CHECK(sender IN ('patient', 'bot')),
    text TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    rag_confidence REAL,  -- NULL for non-RAG messages (e.g., escalations)
    escalated_flag BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary query: get conversation history for a patient
CREATE INDEX IF NOT EXISTS idx_patient_timestamp
    ON patient_conversations(patient_id, timestamp);

-- Support cleanup queries
CREATE INDEX IF NOT EXISTS idx_timestamp
    ON patient_conversations(timestamp);

-- Support escalation tracking
CREATE INDEX IF NOT EXISTS idx_escalated_flag
    ON patient_conversations(escalated_flag, timestamp);

-- ============================================================================
-- Foreign Key Constraint (optional, for referential integrity)
-- ============================================================================
-- Note: Uncomment if you want to enforce that patient_id exists in HIS database
-- ALTER TABLE patient_conversations
-- ADD CONSTRAINT fk_patient_id FOREIGN KEY (patient_id) REFERENCES his_patients(patient_id);
