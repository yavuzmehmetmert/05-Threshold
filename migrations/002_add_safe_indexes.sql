-- ============================================================================
-- Safe Indexes on Existing Public Tables
-- ONLY adds indexes, does NOT modify columns or data
-- ============================================================================

-- Existing tables may already have some indexes, so use IF NOT EXISTS

-- Activities: Optimize user + date queries
CREATE INDEX IF NOT EXISTS idx_activities_user_date 
    ON public.activities(user_id, local_start_date DESC);

-- Activity Streams: Optimize activity + timestamp queries
CREATE INDEX IF NOT EXISTS idx_activity_streams_activity_timestamp 
    ON public.activity_streams(activity_id, timestamp);

-- Sleep Logs: Optimize user + date queries
CREATE INDEX IF NOT EXISTS idx_sleep_logs_user_date 
    ON public.sleep_logs(user_id, calendar_date DESC);

-- HRV Logs: Optimize user + date queries
CREATE INDEX IF NOT EXISTS idx_hrv_logs_user_date 
    ON public.hrv_logs(user_id, calendar_date DESC);

-- Stress Logs: Optimize user + date queries
CREATE INDEX IF NOT EXISTS idx_stress_logs_user_date 
    ON public.stress_logs(user_id, calendar_date DESC);

-- Physiological Logs: Optimize user + date queries
CREATE INDEX IF NOT EXISTS idx_physiological_logs_user_date 
    ON public.physiological_logs(user_id, calendar_date DESC);
