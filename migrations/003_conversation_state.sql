-- Coach V2: Conversation State Table
-- Stores pinned activity context for multi-turn conversations

CREATE TABLE IF NOT EXISTS coach_v2.conversation_state (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    pinned_garmin_activity_id BIGINT,
    pinned_local_start_date DATE,
    pinned_activity_name TEXT,
    pinned_expires_at TIMESTAMP DEFAULT now() + INTERVAL '30 minutes',
    last_intent TEXT,
    updated_at TIMESTAMP DEFAULT now()
);

-- Index for cleanup of expired states
CREATE INDEX IF NOT EXISTS idx_conversation_state_expires 
    ON coach_v2.conversation_state(pinned_expires_at);

COMMENT ON TABLE coach_v2.conversation_state IS 
    'Stores pinned activity/date context for multi-turn coach conversations';
