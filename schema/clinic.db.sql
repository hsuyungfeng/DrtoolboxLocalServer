-- clinic.db Schema
-- Clinic-specific operational database including schedules, protocols, procedures, and staff info
-- Created: 2026-05-07

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================================
-- Clinic Information Tables
-- ============================================================================

-- Clinic basic information (診所基本資訊)
CREATE TABLE IF NOT EXISTS clinic_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_name TEXT NOT NULL UNIQUE,
    clinic_name_english TEXT,
    clinic_name_chinese TEXT NOT NULL,

    -- Contact information
    phone TEXT,
    fax TEXT,
    email TEXT,
    website TEXT,

    -- Address
    address TEXT NOT NULL,
    district TEXT,  -- 區域 (e.g., '信義區', '中正區')
    city TEXT,      -- 城市 (e.g., '台北市')
    postal_code TEXT,
    gps_latitude REAL,
    gps_longitude REAL,

    -- Operations
    established_year INTEGER,
    department_type TEXT,  -- '內科', '外科', '牙科', etc.
    specialties TEXT,  -- JSON array of specialties

    -- Staff
    director_name TEXT,
    director_title TEXT,
    staff_count INTEGER,

    -- Facilities
    num_beds INTEGER,
    has_imaging BOOLEAN DEFAULT 0,  -- X-ray, ultrasound, etc.
    has_lab BOOLEAN DEFAULT 0,
    has_emergency BOOLEAN DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT
);

-- ============================================================================
-- Clinic Schedule Tables (門診時間表)
-- ============================================================================

-- Weekly clinic schedules
CREATE TABLE IF NOT EXISTS clinic_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,  -- '星期一', '星期二', etc. (Monday-Sunday)
    day_number INTEGER,  -- 1-7 (Monday=1, Sunday=7)

    -- Morning session (上午)
    morning_start TIME,
    morning_end TIME,
    morning_doctor TEXT,  -- Doctor name or ID
    morning_capacity INTEGER,  -- Max patients

    -- Afternoon session (下午)
    afternoon_start TIME,
    afternoon_end TIME,
    afternoon_doctor TEXT,
    afternoon_capacity INTEGER,

    -- Evening session (晚上)
    evening_start TIME,
    evening_end TIME,
    evening_doctor TEXT,
    evening_capacity INTEGER,

    -- Status
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Holiday schedules (特殊時間、休診日)
CREATE TABLE IF NOT EXISTS clinic_holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    holiday_date DATE NOT NULL,
    holiday_name TEXT,  -- '春節', '端午節', '公眾假期', '特殊休診', etc.
    is_closed BOOLEAN DEFAULT 1,  -- If 0, special hours apply
    special_hours_start TIME,
    special_hours_end TIME,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Staff and Personnel Tables
-- ============================================================================

-- Medical staff (醫療人員)
CREATE TABLE IF NOT EXISTS clinic_staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    staff_id TEXT UNIQUE,  -- Employee ID
    staff_name TEXT NOT NULL,
    staff_name_english TEXT,

    -- Credentials
    position TEXT,  -- '主治醫師', '住院醫師', '護士', '技術員', '行政助理', etc.
    specialty TEXT,  -- Medical specialty if applicable
    license_number TEXT,  -- Medical/nursing license
    license_expiry DATE,

    -- Contact
    phone TEXT,
    email TEXT,

    -- Schedule
    available_days TEXT,  -- JSON array of days
    shift_type TEXT,  -- 'full-time', 'part-time', 'on-call'

    -- Status
    is_active BOOLEAN DEFAULT 1,
    hire_date DATE,
    termination_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Protocols and Procedures (診所Protocol和日常資訊)
-- ============================================================================

-- Clinical protocols (診療Protocol)
CREATE TABLE IF NOT EXISTS clinic_protocols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    protocol_name TEXT NOT NULL,
    protocol_category TEXT,  -- '檢查', '檢驗', '用藥', '感染控制', '急救', etc.

    description TEXT,
    procedure_steps TEXT,  -- JSON array of steps
    equipment_needed TEXT,  -- JSON array
    safety_precautions TEXT,  -- JSON array
    responsible_staff TEXT,  -- Position required to perform

    -- Clinical information
    indication TEXT,  -- When to use this protocol
    contraindications TEXT,  -- JSON array
    expected_outcome TEXT,
    complications TEXT,  -- Possible complications

    -- Documentation
    created_by TEXT,  -- Staff member ID
    last_reviewed_by TEXT,
    last_reviewed_date DATE,
    approval_status TEXT,  -- 'approved', 'pending', 'archived'

    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Standard operating procedures (日常操作流程)
CREATE TABLE IF NOT EXISTS clinic_sop (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    sop_name TEXT NOT NULL,  -- e.g., '患者登記流程', '掛號程序', '計費流程'
    sop_category TEXT,  -- '前台', '醫療', '後勤', '行政', etc.

    description TEXT,
    steps TEXT,  -- JSON array of procedure steps
    responsible_person TEXT,  -- Job title
    time_estimate INTEGER,  -- Minutes
    tools_needed TEXT,  -- JSON array
    documentation_required TEXT,  -- JSON array

    -- Compliance
    regulatory_reference TEXT,  -- Related regulations
    review_frequency TEXT,  -- 'monthly', 'quarterly', 'yearly'
    last_reviewed_date DATE,

    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Clinic Resources and Equipment (設備和資源)
-- ============================================================================

-- Medical equipment (醫療設備)
CREATE TABLE IF NOT EXISTS clinic_equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    equipment_id TEXT UNIQUE,
    equipment_name TEXT NOT NULL,
    equipment_type TEXT,  -- '診斷', '治療', '監測', '輔助', etc.

    -- Details
    model TEXT,
    manufacturer TEXT,
    serial_number TEXT,

    -- Maintenance
    purchase_date DATE,
    warranty_expiry DATE,
    maintenance_schedule TEXT,  -- 'monthly', 'quarterly', etc.
    last_maintenance_date DATE,
    next_maintenance_date DATE,
    maintenance_provider TEXT,

    -- Calibration (校準)
    requires_calibration BOOLEAN DEFAULT 0,
    last_calibration_date DATE,
    next_calibration_date DATE,
    calibration_provider TEXT,

    -- Status
    is_operational BOOLEAN DEFAULT 1,
    location TEXT,  -- Room or area
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Consumables and supplies (耗材和物資)
CREATE TABLE IF NOT EXISTS clinic_supplies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    supply_name TEXT NOT NULL,
    supply_category TEXT,  -- '藥物', '器材', '耗材', '清潔用品', etc.

    -- Inventory
    quantity_on_hand INTEGER,
    minimum_quantity INTEGER,  -- Reorder point
    maximum_quantity INTEGER,
    unit TEXT,  -- 'box', 'bottle', 'package', etc.

    -- Supplier info
    supplier_name TEXT,
    supplier_contact TEXT,
    supplier_phone TEXT,
    lead_time_days INTEGER,

    -- Cost
    unit_cost REAL,
    currency TEXT DEFAULT 'TWD',

    -- Tracking
    last_ordered_date DATE,
    last_received_date DATE,
    expiry_date DATE,
    batch_number TEXT,

    -- Status
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Clinic Policies and Guidelines (診所政策和指南)
-- ============================================================================

-- Clinic policies (診所政策)
CREATE TABLE IF NOT EXISTS clinic_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    policy_name TEXT NOT NULL,
    policy_category TEXT,  -- '患者權利', '感染控制', '隱私', '計費', '投訴', etc.

    description TEXT,
    policy_content TEXT,  -- Full policy text
    effective_date DATE,
    expiry_date DATE,

    -- Compliance
    regulatory_basis TEXT,  -- Related laws/regulations
    applies_to TEXT,  -- JSON array of staff roles

    -- Review
    last_reviewed_date DATE,
    next_review_date DATE,
    reviewed_by TEXT,  -- Staff member ID
    version INTEGER DEFAULT 1,

    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Patient Communication and Forms (患者溝通和表格)
-- ============================================================================

-- Patient forms and templates (患者表格模板)
CREATE TABLE IF NOT EXISTS clinic_forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    form_name TEXT NOT NULL,
    form_category TEXT,  -- '初診', '同意書', '病歷', '檢查', '投訴', etc.

    description TEXT,
    form_template TEXT,  -- Template content or path
    required_fields TEXT,  -- JSON array of field names
    is_required BOOLEAN DEFAULT 0,  -- Is this form mandatory
    language TEXT DEFAULT 'zh_TW',  -- Traditional Chinese

    version INTEGER DEFAULT 1,
    created_by TEXT,
    last_updated_by TEXT,

    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Clinic Events and Announcements (診所事件和公告)
-- ============================================================================

-- Important announcements and notices (重要公告)
CREATE TABLE IF NOT EXISTS clinic_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    announcement_title TEXT NOT NULL,
    announcement_category TEXT,  -- '通知', '警告', '更新', '特殊服務', etc.

    content TEXT,
    announcement_date DATE,
    start_date DATE,
    end_date DATE,

    priority TEXT,  -- 'high', 'medium', 'low'
    target_audience TEXT,  -- '患者', '職員', '兩者', etc.
    is_published BOOLEAN DEFAULT 0,

    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Clinic Statistics and Reports (統計和報告)
-- ============================================================================

-- Daily operations log (日報)
CREATE TABLE IF NOT EXISTS clinic_daily_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clinic_id INTEGER NOT NULL,
    log_date DATE NOT NULL,

    -- Patient statistics
    total_patients_seen INTEGER,
    new_patients INTEGER,
    returning_patients INTEGER,

    -- Session statistics
    morning_patients INTEGER,
    afternoon_patients INTEGER,
    evening_patients INTEGER,

    -- Operations
    emergency_cases INTEGER,
    referrals_out INTEGER,
    referrals_in INTEGER,

    -- Equipment/resource issues
    equipment_issues TEXT,  -- JSON array
    supply_shortages TEXT,  -- JSON array

    -- Staff
    staff_on_duty TEXT,  -- JSON array of staff IDs
    absent_staff TEXT,  -- JSON array

    -- Notes
    significant_events TEXT,
    issues_encountered TEXT,
    notes TEXT,

    logged_by TEXT,  -- Staff member ID
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_clinic_schedules_full
    ON clinic_schedules(clinic_id, day_of_week);

CREATE INDEX IF NOT EXISTS idx_clinic_staff_active
    ON clinic_staff(clinic_id, is_active);

CREATE INDEX IF NOT EXISTS idx_clinic_equipment_operational
    ON clinic_equipment(clinic_id, is_operational);

CREATE INDEX IF NOT EXISTS idx_clinic_supplies_inventory
    ON clinic_supplies(clinic_id, quantity_on_hand, minimum_quantity);

CREATE INDEX IF NOT EXISTS idx_clinic_protocols_active
    ON clinic_protocols(clinic_id, is_active, protocol_category);

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View: Clinic operating hours this week
CREATE VIEW IF NOT EXISTS v_clinic_hours_this_week AS
SELECT
    cs.clinic_id,
    cs.day_of_week,
    cs.morning_start,
    cs.morning_end,
    cs.afternoon_start,
    cs.afternoon_end,
    cs.evening_start,
    cs.evening_end,
    COALESCE(cs.morning_capacity, 0) +
    COALESCE(cs.afternoon_capacity, 0) +
    COALESCE(cs.evening_capacity, 0) as total_capacity
FROM clinic_schedules cs
WHERE cs.is_active = 1;

-- View: Supplies needing reorder
CREATE VIEW IF NOT EXISTS v_supplies_low_stock AS
SELECT
    clinic_id,
    supply_name,
    quantity_on_hand,
    minimum_quantity,
    supplier_name,
    supplier_contact
FROM clinic_supplies
WHERE is_active = 1
  AND quantity_on_hand <= minimum_quantity;

-- View: Equipment maintenance schedule
CREATE VIEW IF NOT EXISTS v_equipment_maintenance_schedule AS
SELECT
    clinic_id,
    equipment_name,
    equipment_type,
    next_maintenance_date,
    maintenance_provider,
    last_maintenance_date
FROM clinic_equipment
WHERE is_operational = 1
ORDER BY next_maintenance_date ASC;

-- View: Active protocols by category
CREATE VIEW IF NOT EXISTS v_active_protocols AS
SELECT
    clinic_id,
    protocol_category,
    protocol_name,
    responsible_staff,
    version,
    last_reviewed_date
FROM clinic_protocols
WHERE is_active = 1
ORDER BY protocol_category, protocol_name;

-- View: Active staff by position
CREATE VIEW IF NOT EXISTS v_active_staff_roster AS
SELECT
    clinic_id,
    position,
    COUNT(*) as staff_count,
    GROUP_CONCAT(staff_name) as staff_names
FROM clinic_staff
WHERE is_active = 1
GROUP BY clinic_id, position;

-- ============================================================================
-- HIS Query Cache Table (Phase 2 Integration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,  -- SHA256(query + json.dumps(params))
    query_text TEXT NOT NULL,
    query_params TEXT,  -- JSON-encoded tuple
    result_json TEXT NOT NULL,  -- JSON-encoded result
    ttl_seconds INTEGER DEFAULT 3600,  -- Per D-02: 1 hour default
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (datetime('now', '+1 hour')),
    hit_count INTEGER DEFAULT 0,
    is_valid BOOLEAN DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_cache_hash
    ON query_cache(query_hash);

CREATE INDEX IF NOT EXISTS idx_query_cache_expires
    ON query_cache(expires_at);

-- ============================================================================
-- Patient Intake Tables (Phase 3 - Patient Engagement)
-- ============================================================================

-- Patients (患者)
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    dob DATE NOT NULL,
    medical_history TEXT,
    allergies TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    created_by TEXT,
    updated_by TEXT
);

-- Appointments (掛號/預約)
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    appointment_date DATE NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- LINE User Mapping (LINE用戶映射)
CREATE TABLE IF NOT EXISTS line_user_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_user_id TEXT UNIQUE NOT NULL,
    patient_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    linked_by TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- ============================================================================
-- Patient Intake Indices
-- ============================================================================

-- Unique composite index for phone+email deduplication (per D-03 idempotency)
CREATE UNIQUE INDEX IF NOT EXISTS idx_patients_phone_email
    ON patients(phone, email);

-- Index for created_at queries
CREATE INDEX IF NOT EXISTS idx_patients_created
    ON patients(created_at);

-- Index for appointment lookups by patient
CREATE INDEX IF NOT EXISTS idx_appointments_patient
    ON appointments(patient_id);

-- Index for line user mapping lookups
CREATE INDEX IF NOT EXISTS idx_line_user_mapping_patient
    ON line_user_mapping(patient_id);

-- ============================================================================
-- Conversation History Table (Phase 3 - Patient Conversations)
-- ============================================================================

-- Patient conversation history (patient-bot interactions)
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
-- Conversation History Indexes (Performance)
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
