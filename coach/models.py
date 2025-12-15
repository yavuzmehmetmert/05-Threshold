"""
Coach Module SQLAlchemy Models
Database models for AI Running Coach "Hoca"
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, LargeBinary, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class CoachConversationState(Base):
    """
    Rolling summary of conversation - NOT full chat logs.
    Token-efficient: stores compressed state instead of raw messages.
    """
    __tablename__ = "coach_conversation_state"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Rolling summary of conversation (~800 chars max)
    rolling_summary = Column(Text, default="")
    
    # Last user goal/focus (~300 chars max)
    last_user_goal = Column(Text, default="")
    
    # Compact last 3 turns as JSON array (~1200 chars total)
    # Format: [{"role":"user","msg":"...truncated"}, {"role":"assistant","msg":"...truncated"}]
    last_turns_compact = Column(JSON, default=list)
    
    # Metadata
    turn_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class CoachUserFacts(Base):
    """
    Stable facts about the user extracted by AI during "learn" phase.
    These rarely change and are used as context in every request.
    """
    __tablename__ = "coach_user_facts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # AI-extracted stable facts about user (~500 chars)
    # e.g., "Marathon goal: Sub-3:30. Injury history: IT band 2023. Prefers morning runs."
    facts_summary = Column(Text, default="")
    
    # Training philosophy notes
    training_preferences = Column(Text, default="")
    
    # Key milestones/achievements
    achievements = Column(Text, default="")
    
    # Last analysis timestamp
    last_analyzed_at = Column(DateTime, nullable=True)
    activities_analyzed_count = Column(Integer, default=0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class CoachBriefing(Base):
    """
    Daily briefings cached to avoid regeneration.
    Generated on-demand, cached for the day.
    """
    __tablename__ = "coach_briefings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    briefing_date = Column(Date, nullable=False, index=True)
    
    # Structured briefing content
    greeting = Column(Text)
    training_status = Column(Text)
    today_recommendation = Column(Text)
    recovery_notes = Column(Text)
    motivation = Column(Text)
    
    # Full rendered briefing
    full_text = Column(Text)
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    tokens_used = Column(Integer)
    
    __table_args__ = (
        # Unique constraint for user + date
        {"sqlite_autoincrement": True},
    )


class CoachNote(Base):
    """
    User notes to coach (manual input like injuries, goals, feedback).
    """
    __tablename__ = "coach_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    
    note_type = Column(String(50), default="general")  # general, injury, goal, feedback
    content = Column(Text, nullable=False)
    
    # AI processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class CoachKnowledgeChunk(Base):
    """
    RAG knowledge base chunks from training science documents.
    Used for retrieval-augmented generation.
    """
    __tablename__ = "coach_knowledge_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Source document info
    source_doc = Column(String(255), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    
    # Metadata for filtering
    topic = Column(String(100), index=True)  # training, nutrition, injury, recovery, technique, physiology
    subtopic = Column(String(100))
    keywords = Column(JSON, default=list)  # array of keywords for BM25
    
    # Token count estimate
    token_estimate = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        # Unique constraint for source + index
        {"sqlite_autoincrement": True},
    )
