-- ============================================================================
-- Coach V2 Schema Migration
-- Creates new coach_v2 schema with all required tables
-- Does NOT modify any existing public tables
-- ============================================================================

-- Create schema
CREATE SCHEMA IF NOT EXISTS coach_v2;

-- ============================================================================
-- Table: activity_summaries
-- Bounded per-activity summary with canonical facts
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.activity_summaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id),
    garmin_activity_id BIGINT NOT NULL,
    
    -- Bounded summary content
    facts_text VARCHAR(600) NOT NULL,           -- BEGIN_FACTS...END_FACTS block
    summary_text VARCHAR(1200) NOT NULL,        -- Human-readable summary
    summary_json JSONB,                          -- Structured data for programmatic access
    
    -- Metadata
    local_start_date DATE NOT NULL,
    workout_type VARCHAR(20),                   -- interval, tempo, easy, long, unknown
    version INTEGER DEFAULT 1,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(user_id, garmin_activity_id)
);

CREATE INDEX IF NOT EXISTS idx_activity_summaries_user_date 
    ON coach_v2.activity_summaries(user_id, local_start_date DESC);

CREATE INDEX IF NOT EXISTS idx_activity_summaries_garmin_id 
    ON coach_v2.activity_summaries(garmin_activity_id);

-- ============================================================================
-- Table: user_model
-- Per-user learned model (28-day rolling window)
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.user_model (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) UNIQUE,
    
    -- Model content (bounded to ~4KB)
    model_json JSONB NOT NULL DEFAULT '{}',
    
    -- Configuration
    window_days INTEGER DEFAULT 28,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Validation: model_json should be < 4KB
    CONSTRAINT model_json_size CHECK (length(model_json::text) < 4096)
);

-- ============================================================================
-- Table: insights
-- Daily generated insights with evidence
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id),
    insight_date DATE NOT NULL,
    
    -- Content (bounded)
    insight_text VARCHAR(600) NOT NULL,
    evidence_refs JSONB,                        -- References to activities/biometrics
    
    -- Quality
    confidence FLOAT DEFAULT 0.5,               -- 0.0 to 1.0
    insight_type VARCHAR(50),                   -- trend, warning, achievement, recommendation
    status VARCHAR(20) DEFAULT 'active',        -- active, dismissed, actioned
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(user_id, insight_date, insight_text)
);

CREATE INDEX IF NOT EXISTS idx_insights_user_date 
    ON coach_v2.insights(user_id, insight_date DESC);

-- ============================================================================
-- Table: daily_briefings
-- Pre-computed morning briefings
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.daily_briefings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id),
    briefing_date DATE NOT NULL,
    
    -- Content (bounded)
    briefing_text VARCHAR(1500) NOT NULL,
    sources_json JSONB,                         -- What data was used to generate
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(user_id, briefing_date)
);

CREATE INDEX IF NOT EXISTS idx_briefings_user_date 
    ON coach_v2.daily_briefings(user_id, briefing_date DESC);

-- ============================================================================
-- Table: kb_docs
-- Knowledge base documents (PDFs, articles)
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.kb_docs (
    id SERIAL PRIMARY KEY,
    
    -- Document metadata
    title VARCHAR(500) NOT NULL,
    source_type VARCHAR(50),                    -- pdf, article, manual
    source_path VARCHAR(1000),
    
    -- Content
    full_text TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Table: kb_chunks
-- RAG chunks for knowledge base (with full-text search)
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.kb_chunks (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES coach_v2.kb_docs(id) ON DELETE CASCADE,
    
    -- Chunk content
    chunk_index INTEGER NOT NULL,
    content VARCHAR(2000) NOT NULL,
    
    -- Optional: embedding for vector search (pgvector)
    -- embedding vector(768),  -- Uncomment when pgvector is available
    
    -- Full-text search
    content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('turkish', content)) STORED,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc 
    ON coach_v2.kb_chunks(doc_id);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_fts 
    ON coach_v2.kb_chunks USING GIN(content_tsv);

-- ============================================================================
-- Table: notes
-- User notes on activities
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id),
    garmin_activity_id BIGINT,                  -- Optional: note on specific activity
    
    -- Content
    note_text VARCHAR(2000) NOT NULL,
    note_type VARCHAR(50) DEFAULT 'general',    -- general, injury, goal, feeling
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_user 
    ON coach_v2.notes(user_id, created_at DESC);

-- ============================================================================
-- Table: pipeline_runs
-- Track nightly pipeline execution
-- ============================================================================
CREATE TABLE IF NOT EXISTS coach_v2.pipeline_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id),
    
    -- Run info
    run_type VARCHAR(50) NOT NULL,              -- nightly, manual, incremental
    status VARCHAR(20) NOT NULL,                -- running, completed, failed
    
    -- Metrics
    activities_processed INTEGER DEFAULT 0,
    insights_generated INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- ============================================================================
-- View: v_activities_core
-- Read-only view on public.activities with key columns
-- ============================================================================
CREATE OR REPLACE VIEW coach_v2.v_activities_core AS
SELECT 
    a.id,
    a.activity_id AS garmin_activity_id,
    a.user_id,
    a.activity_name,
    a.start_time_local,
    a.local_start_date,
    a.activity_type,
    a.distance,
    a.duration,
    a.average_hr,
    a.max_hr,
    a.rpe,
    a.training_effect,
    a.aerobic_te,
    a.anaerobic_te,
    a.vo2_max,
    a.recovery_time,
    a.avg_cadence,
    a.avg_stride_length,
    a.elevation_gain,
    a.weather_temp,
    a.weather_condition,
    a.raw_json,
    a.metadata_blob
FROM public.activities a;

-- ============================================================================
-- View: v_biometrics_7d
-- 7-day biometrics summary view
-- ============================================================================
CREATE OR REPLACE VIEW coach_v2.v_biometrics_7d AS
SELECT 
    u.id AS user_id,
    (SELECT AVG(s.sleep_score) FROM public.sleep_logs s 
     WHERE s.user_id = u.id AND s.calendar_date >= CURRENT_DATE - 7) AS avg_sleep_score,
    (SELECT AVG(h.last_night_avg) FROM public.hrv_logs h 
     WHERE h.user_id = u.id AND h.calendar_date >= CURRENT_DATE - 7) AS avg_hrv,
    (SELECT AVG(st.avg_stress) FROM public.stress_logs st 
     WHERE st.user_id = u.id AND st.calendar_date >= CURRENT_DATE - 7) AS avg_stress,
    (SELECT COUNT(*) FROM public.activities a 
     WHERE a.user_id = u.id AND a.local_start_date >= CURRENT_DATE - 7) AS activity_count_7d,
    (SELECT SUM(a.distance) FROM public.activities a 
     WHERE a.user_id = u.id AND a.local_start_date >= CURRENT_DATE - 7) AS total_distance_7d
FROM public.users u;
