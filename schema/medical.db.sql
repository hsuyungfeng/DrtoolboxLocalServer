-- medical.db Schema
-- General medical knowledge base including medical knowledge, case templates, and references
-- Created: 2026-05-07

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================================
-- Medical Knowledge Tables
-- ============================================================================

-- General medical knowledge from medical_o1_sft_Chinese.json
CREATE TABLE IF NOT EXISTS medical_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,  -- e.g., '糖尿病', '高血壓', '感冒'
    subcategory TEXT,  -- e.g., 'Type 1', 'Type 2', etc.
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,  -- comma-separated for search
    language TEXT DEFAULT 'zh_TW',  -- Traditional Chinese
    source TEXT,  -- source from JSON
    confidence REAL,  -- 0.0-1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Medical conditions/diseases reference
CREATE TABLE IF NOT EXISTS medical_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_name TEXT NOT NULL UNIQUE,
    description TEXT,
    symptoms TEXT,  -- JSON array of symptoms
    causes TEXT,  -- JSON array of causes
    risk_factors TEXT,  -- JSON array of risk factors
    treatment_options TEXT,  -- JSON array of treatments
    prevention TEXT,
    severity_levels TEXT,  -- JSON: mild, moderate, severe, critical
    icd_code TEXT,  -- International Classification of Diseases
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Medical treatments and medications
CREATE TABLE IF NOT EXISTS medical_treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    treatment_name TEXT NOT NULL,
    condition_id INTEGER,
    treatment_type TEXT,  -- e.g., 'medication', 'therapy', 'procedure'
    description TEXT,
    effectiveness REAL,  -- 0.0-1.0
    side_effects TEXT,  -- JSON array
    contraindications TEXT,  -- JSON array of conditions
    dosage TEXT,
    duration TEXT,
    cost_estimate TEXT,
    evidence_level TEXT,  -- 'strong', 'moderate', 'weak'
    source_references TEXT,  -- JSON array of sources
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Case Templates (1,665 cases)
-- ============================================================================

CREATE TABLE IF NOT EXISTS case_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT NOT NULL UNIQUE,
    case_name TEXT NOT NULL,
    patient_age INTEGER,
    patient_gender TEXT,  -- 'M', 'F', 'Other'
    chief_complaint TEXT NOT NULL,  -- 主訴

    -- Medical history
    medical_history TEXT,
    allergies TEXT,  -- JSON array
    current_medications TEXT,  -- JSON array

    -- Case presentation
    presentation_text TEXT NOT NULL,
    symptoms TEXT,  -- JSON array
    vital_signs TEXT,  -- JSON: blood pressure, heart rate, temp, etc.
    physical_exam TEXT,

    -- Diagnostic information
    preliminary_diagnosis TEXT,
    differential_diagnoses TEXT,  -- JSON array
    diagnostic_tests TEXT,  -- JSON array of tests performed
    test_results TEXT,  -- JSON object of results
    final_diagnosis TEXT NOT NULL,

    -- Treatment and outcome
    treatment_plan TEXT,
    medications_prescribed TEXT,  -- JSON array
    procedures_performed TEXT,  -- JSON array
    follow_up_plan TEXT,
    outcome TEXT,  -- 'recovered', 'improved', 'stable', 'deceased'
    recovery_time_days INTEGER,

    -- Educational value
    learning_points TEXT,  -- JSON array of key learnings
    difficulty_level TEXT,  -- 'beginner', 'intermediate', 'advanced'
    specialty TEXT,  -- e.g., 'cardiology', 'neurology', '內科'

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Case-related documents/images
CREATE TABLE IF NOT EXISTS case_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    attachment_type TEXT,  -- 'image', 'document', 'lab_result'
    file_path TEXT,
    file_name TEXT,
    file_size INTEGER,
    mime_type TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Medical References and Guidelines
-- ============================================================================

CREATE TABLE IF NOT EXISTS medical_guidelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guideline_name TEXT NOT NULL,
    condition_id INTEGER,
    organization TEXT,  -- e.g., 'WHO', '台灣醫學會'
    publication_year INTEGER,
    description TEXT,
    recommendations TEXT,  -- JSON array of recommendations
    evidence_summary TEXT,
    link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Medical terminology and translations
CREATE TABLE IF NOT EXISTS medical_terminology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english_term TEXT NOT NULL,
    chinese_term TEXT NOT NULL,
    traditional_chinese TEXT,
    simplified_chinese TEXT,
    pronunciation_pinyin TEXT,
    definition TEXT,
    usage_context TEXT,
    related_terms TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(english_term, traditional_chinese)
);

-- ============================================================================
-- Ingestion Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT,
    source_type TEXT,  -- 'json', 'pdf', 'csv', 'database'
    table_name TEXT,
    records_imported INTEGER,
    records_failed INTEGER,
    import_status TEXT,  -- 'success', 'partial', 'failed'
    error_details TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    imported_by TEXT
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_medical_knowledge_full_text
    ON medical_knowledge(category, subcategory, title, keywords);

CREATE INDEX IF NOT EXISTS idx_case_templates_search
    ON case_templates(case_name, specialty, final_diagnosis);

CREATE INDEX IF NOT EXISTS idx_case_templates_time
    ON case_templates(created_at, updated_at);

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View: Cases by specialty with counts
CREATE VIEW IF NOT EXISTS v_cases_by_specialty AS
SELECT
    specialty,
    COUNT(*) as case_count,
    GROUP_CONCAT(DISTINCT difficulty_level) as difficulty_levels
FROM case_templates
WHERE is_active = 1
GROUP BY specialty;

-- View: Treatments for a condition
CREATE VIEW IF NOT EXISTS v_condition_treatments AS
SELECT
    c.condition_name,
    t.treatment_name,
    t.treatment_type,
    t.effectiveness,
    t.evidence_level
FROM medical_conditions c
LEFT JOIN medical_treatments t ON c.id = t.condition_id
WHERE c.id IS NOT NULL;

-- View: Medical knowledge by category
CREATE VIEW IF NOT EXISTS v_knowledge_by_category AS
SELECT
    category,
    subcategory,
    COUNT(*) as article_count,
    GROUP_CONCAT(DISTINCT title) as articles
FROM medical_knowledge
WHERE is_active = 1
GROUP BY category, subcategory;
