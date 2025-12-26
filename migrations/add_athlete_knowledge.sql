-- Athlete Knowledge System Migration
-- Created: 2024-12-26
-- Purpose: Enable hOCA to truly know the athlete through health/life event tracking

-- ============================================================================
-- CONDITION TYPES TABLE
-- Defines categories of conditions with their impact levels and follow-up rules
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.condition_types (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,            -- 'shin_splint', 'thyroid', 'alcohol', 'work_stress'
    category TEXT NOT NULL,               -- 'injury', 'chronic', 'lifestyle', 'mental', 'life_event'
    impact_level TEXT DEFAULT 'acute',    -- 'acute' (time-based aging), 'recurring', 'chronic' (never ages)
    default_followup_days INT[],          -- [3, 7, 14] for acute, NULL for chronic
    affects_training BOOLEAN DEFAULT TRUE,
    description TEXT,                     -- Human-readable description for LLM context
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ATHLETE HEALTH LOG TABLE (Type-2 / Append-Only)
-- Every event is a new row - no updates, only appends
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.athlete_health_log (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    condition_id UUID NOT NULL,           -- Groups events for same condition instance
    condition_type_id INT REFERENCES coach_v2.condition_types(id),
    event_type TEXT NOT NULL,             -- 'onset', 'update', 'resolved', 'relapse', 'followup_asked', 'followup_response'
    event_date DATE NOT NULL,
    description TEXT,                     -- LLM-extracted or user-provided description
    source TEXT DEFAULT 'self_report',    -- 'self_report', 'professional', 'coach_inference'
    confidence FLOAT DEFAULT 0.7,         -- 0.0-1.0 confidence in the information
    severity INT DEFAULT 3,               -- 1-5 scale (1=minor, 5=severe)
    raw_message TEXT,                     -- Original user message that triggered this
    needs_followup BOOLEAN DEFAULT TRUE,  -- Should coach follow up on this?
    followup_scheduled_date DATE,         -- When next follow-up should happen
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast user queries
CREATE INDEX IF NOT EXISTS idx_health_log_user_date 
ON coach_v2.athlete_health_log(user_id, event_date DESC);

-- Index for condition grouping
CREATE INDEX IF NOT EXISTS idx_health_log_condition 
ON coach_v2.athlete_health_log(condition_id, created_at DESC);

-- ============================================================================
-- ACTIVE CONDITIONS VIEW
-- Latest state per condition instance
-- ============================================================================
CREATE OR REPLACE VIEW coach_v2.active_conditions AS
SELECT DISTINCT ON (ahl.condition_id)
    ahl.id,
    ahl.user_id,
    ahl.condition_id,
    ahl.condition_type_id,
    ahl.event_type,
    ahl.event_date,
    ahl.description,
    ahl.source,
    ahl.confidence,
    ahl.severity,
    ahl.needs_followup,
    ahl.followup_scheduled_date,
    ahl.created_at,
    ct.name as condition_name,
    ct.category,
    ct.impact_level,
    ct.default_followup_days,
    ct.affects_training,
    ct.description as condition_description
FROM coach_v2.athlete_health_log ahl
LEFT JOIN coach_v2.condition_types ct ON ahl.condition_type_id = ct.id
ORDER BY ahl.condition_id, ahl.created_at DESC;

-- ============================================================================
-- DEFAULT CONDITION TYPES
-- LLM will match detected conditions to these types
-- ============================================================================
INSERT INTO coach_v2.condition_types (name, category, impact_level, default_followup_days, affects_training, description)
VALUES
    -- INJURIES (mostly acute or recurring)
    ('shin_splint', 'injury', 'recurring', ARRAY[3, 7, 14], TRUE, 'Kaval kemiği ağrısı - koşu hacmini azaltmayı gerektirir'),
    ('knee_pain', 'injury', 'recurring', ARRAY[3, 7, 14], TRUE, 'Diz ağrısı - nedene göre tedavi değişir'),
    ('achilles', 'injury', 'recurring', ARRAY[3, 7, 14, 30], TRUE, 'Aşil tendonu sorunu - uzun iyileşme süreci'),
    ('plantar_fasciitis', 'injury', 'recurring', ARRAY[7, 14, 30], TRUE, 'Tabanlık iltihabı - sabah ağrısı karakteristik'),
    ('muscle_strain', 'injury', 'acute', ARRAY[3, 7], TRUE, 'Kas zorlanması - genelde 1-2 hafta iyileşme'),
    ('back_pain', 'injury', 'recurring', ARRAY[3, 7, 14], TRUE, 'Bel ağrısı - koşu formunu etkiler'),
    ('ankle_sprain', 'injury', 'acute', ARRAY[3, 7, 14], TRUE, 'Ayak bileği burkulması'),
    ('general_injury', 'injury', 'acute', ARRAY[3, 7], TRUE, 'Genel sakatlık'),
    
    -- CHRONIC CONDITIONS (never age out)
    ('thyroid', 'chronic', 'chronic', NULL, TRUE, 'Tiroid hastalığı - yüklenme kapasitesini etkiler'),
    ('diabetes', 'chronic', 'chronic', NULL, TRUE, 'Diyabet - kan şekeri takibi gerekir'),
    ('asthma', 'chronic', 'chronic', NULL, TRUE, 'Astım - soğuk/nemli havada dikkat'),
    ('heart_condition', 'chronic', 'chronic', NULL, TRUE, 'Kalp rahatsızlığı - nabız limitlerini etkiler'),
    ('hypertension', 'chronic', 'chronic', NULL, TRUE, 'Hipertansiyon - yoğun antrenmanda dikkat'),
    
    -- LIFESTYLE (short-term impact)
    ('alcohol', 'lifestyle', 'acute', ARRAY[1, 2], TRUE, 'Alkol tüketimi - ertesi gün performansı düşürür'),
    ('poor_sleep', 'lifestyle', 'acute', ARRAY[1, 2], TRUE, 'Kötü uyku - toparlanmayı etkiler'),
    ('travel_fatigue', 'lifestyle', 'acute', ARRAY[2, 3], TRUE, 'Seyahat yorgunluğu'),
    ('illness', 'lifestyle', 'acute', ARRAY[3, 7], TRUE, 'Hastalık (grip, soğuk algınlığı vb.)'),
    
    -- MENTAL (recurring, needs attention)
    ('work_stress', 'mental', 'recurring', ARRAY[7, 14], TRUE, 'İş stresi - motivasyon ve enerjiyi etkiler'),
    ('low_motivation', 'mental', 'recurring', ARRAY[7, 14], TRUE, 'Düşük motivasyon'),
    ('anxiety', 'mental', 'recurring', ARRAY[7, 14], TRUE, 'Anksiyete - yarış kaygısı dahil'),
    ('burnout', 'mental', 'recurring', ARRAY[14, 30], TRUE, 'Tükenmişlik - dinlenme gerektirir'),
    
    -- LIFE EVENTS (major impact, long tracking)
    ('new_job', 'life_event', 'recurring', ARRAY[14, 30], TRUE, 'Yeni iş - program değişikliği'),
    ('new_baby', 'life_event', 'chronic', NULL, TRUE, 'Yeni bebek - uyku ve zaman etkisi'),
    ('moving', 'life_event', 'acute', ARRAY[14, 30], TRUE, 'Taşınma - geçici stres'),
    ('relationship_change', 'life_event', 'recurring', ARRAY[14, 30], TRUE, 'İlişki değişikliği'),
    ('pregnancy', 'life_event', 'chronic', NULL, TRUE, 'Hamilelik - tüm antrenmanı etkiler')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- HELPER FUNCTION: Get relevant conditions for a date range
-- Uses impact-based aging logic
-- ============================================================================
CREATE OR REPLACE FUNCTION coach_v2.get_relevant_conditions(
    p_user_id INT,
    p_target_date DATE DEFAULT CURRENT_DATE,
    p_include_resolved BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    condition_id UUID,
    condition_name TEXT,
    category TEXT,
    impact_level TEXT,
    event_type TEXT,
    event_date DATE,
    description TEXT,
    severity INT,
    days_since_event INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ac.condition_id,
        ac.condition_name,
        ac.category,
        ac.impact_level,
        ac.event_type,
        ac.event_date,
        ac.description,
        ac.severity,
        (p_target_date - ac.event_date)::INT as days_since_event
    FROM coach_v2.active_conditions ac
    WHERE ac.user_id = p_user_id
    AND (
        -- Chronic conditions: ALWAYS include
        ac.impact_level = 'chronic'
        OR
        -- Recurring conditions: Include if within 6 months
        (ac.impact_level = 'recurring' AND ac.event_date > p_target_date - INTERVAL '180 days')
        OR
        -- Acute conditions: Include if within 30 days
        (ac.impact_level = 'acute' AND ac.event_date > p_target_date - INTERVAL '30 days')
    )
    AND (
        -- Include unresolved or optionally resolved
        ac.event_type != 'resolved' OR p_include_resolved
    )
    ORDER BY 
        CASE ac.impact_level 
            WHEN 'chronic' THEN 1 
            WHEN 'recurring' THEN 2 
            ELSE 3 
        END,
        ac.event_date DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- HELPER FUNCTION: Get conditions needing follow-up
-- ============================================================================
CREATE OR REPLACE FUNCTION coach_v2.get_conditions_needing_followup(
    p_user_id INT
)
RETURNS TABLE (
    condition_id UUID,
    condition_name TEXT,
    category TEXT,
    last_event_type TEXT,
    last_event_date DATE,
    description TEXT,
    days_since_event INT,
    followup_reason TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ac.condition_id,
        ac.condition_name,
        ac.category,
        ac.event_type,
        ac.event_date,
        ac.description,
        (CURRENT_DATE - ac.event_date)::INT as days_since,
        CASE 
            WHEN ac.event_type = 'resolved' AND (CURRENT_DATE - ac.event_date) BETWEEN 3 AND 7 
                THEN 'resolved_verification'
            WHEN ac.event_type != 'resolved' AND ac.needs_followup AND ac.followup_scheduled_date <= CURRENT_DATE
                THEN 'scheduled_followup'
            WHEN ac.event_type != 'resolved' AND (CURRENT_DATE - ac.event_date) >= 7
                THEN 'overdue_check'
            ELSE NULL
        END as followup_reason
    FROM coach_v2.active_conditions ac
    WHERE ac.user_id = p_user_id
    AND (
        -- Resolved recently, needs verification
        (ac.event_type = 'resolved' AND (CURRENT_DATE - ac.event_date) BETWEEN 3 AND 7)
        OR
        -- Scheduled follow-up is due
        (ac.event_type != 'resolved' AND ac.needs_followup AND ac.followup_scheduled_date <= CURRENT_DATE)
        OR
        -- No update in 7+ days for active conditions
        (ac.event_type != 'resolved' AND (CURRENT_DATE - ac.event_date) >= 7)
    )
    ORDER BY 
        CASE 
            WHEN ac.event_type = 'resolved' THEN 1  -- Verify resolved first
            ELSE 2 
        END,
        ac.event_date;
END;
$$ LANGUAGE plpgsql;
