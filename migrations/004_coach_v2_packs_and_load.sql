-- Coach V2 Analysis Packs & Training Load Table

-- 1. Activity Analysis Packs
-- Stores pre-computed rich context for activities (LLM-ready)
CREATE TABLE IF NOT EXISTS coach_v2.activity_analysis_packs (
    user_id INTEGER NOT NULL REFERENCES users(id),
    garmin_activity_id BIGINT NOT NULL,
    local_start_date DATE NOT NULL,
    
    -- Compact fact block for LLM context (max 800 chars)
    facts_text TEXT,
    
    -- Pre-formatted markdown tables (laps, intervals, zones)
    tables_markdown TEXT,
    
    -- Coach flags (e.g., ["High Drift", "Negative Split"])
    flags_json JSONB DEFAULT '[]'::jsonb,
    
    -- Structured derived metrics for programmatic checks
    derived_json JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    PRIMARY KEY (user_id, garmin_activity_id)
);

-- Index for date-range queries
CREATE INDEX IF NOT EXISTS idx_packs_date 
    ON coach_v2.activity_analysis_packs(user_id, local_start_date);


-- 2. Daily Training Load
-- Stores calculated fitness/fatigue metrics per day
CREATE TABLE IF NOT EXISTS coach_v2.daily_training_load (
    user_id INTEGER NOT NULL REFERENCES users(id),
    calendar_date DATE NOT NULL,
    
    -- Training Stress Score (Daily Load)
    tss FLOAT DEFAULT 0,
    
    -- Acute Training Load (Fatigue, 7-day avg)
    atl_7 FLOAT DEFAULT 0,
    
    -- Chronic Training Load (Fitness, 42-day avg)
    ctl_42 FLOAT DEFAULT 0,
    
    -- Training Stress Balance (Form, CTL - ATL)
    tsb FLOAT DEFAULT 0,
    
    -- Additional metrics
    ramp_rate_7 FLOAT,
    monotony_7 FLOAT,
    strain_7 FLOAT,
    
    -- Metadata/Notes
    notes_json JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    PRIMARY KEY (user_id, calendar_date)
);

-- Index for longitudinal queries
CREATE INDEX IF NOT EXISTS idx_load_date 
    ON coach_v2.daily_training_load(user_id, calendar_date);

COMMENT ON TABLE coach_v2.activity_analysis_packs IS 
    'Pre-computed rich context packs for LLM consumption per activity';
    
COMMENT ON TABLE coach_v2.daily_training_load IS 
    'Daily calculated fitness/fatigue metrics (ATL/CTL/TSB) for longitudinal tracking';
