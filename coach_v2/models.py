"""
Coach V2 SQLAlchemy Models
==========================

Models for the coach_v2 schema. These are separate from the main models.py
to keep coach_v2 self-contained and portable.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, BigInteger, 
    Text, Date, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class ActivitySummary(Base):
    """Bounded per-activity summary with canonical facts."""
    __tablename__ = "activity_summaries"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garmin_activity_id = Column(BigInteger, nullable=False, unique=True)
    
    # Bounded content
    facts_text = Column(String(600), nullable=False)      # BEGIN_FACTS...END_FACTS
    summary_text = Column(String(1200), nullable=False)   # Human-readable
    summary_json = Column(JSONB)                           # Structured data
    
    # Metadata
    local_start_date = Column(Date, nullable=False)
    workout_type = Column(String(20))  # interval, tempo, easy, long, unknown
    version = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserModel(Base):
    """Per-user learned model (28-day rolling window)."""
    __tablename__ = "user_model"
    __table_args__ = (
        CheckConstraint('length(model_json::text) < 4096', name='model_json_size'),
        {'schema': 'coach_v2', 'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Model content (bounded to ~4KB)
    model_json = Column(JSONB, nullable=False, default={})
    
    # Configuration
    window_days = Column(Integer, default=28)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Insight(Base):
    """Daily generated insights with evidence."""
    __tablename__ = "insights"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    insight_date = Column(Date, nullable=False)
    
    # Content (bounded)
    insight_text = Column(String(600), nullable=False)
    evidence_refs = Column(JSONB)  # References to activities/biometrics
    
    # Quality
    confidence = Column(Float, default=0.5)
    insight_type = Column(String(50))  # trend, warning, achievement, recommendation
    status = Column(String(20), default='active')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyBriefing(Base):
    """Pre-computed morning briefings."""
    __tablename__ = "daily_briefings"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    briefing_date = Column(Date, nullable=False)
    
    # Content (bounded)
    briefing_text = Column(String(1500), nullable=False)
    sources_json = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class KBDoc(Base):
    """Knowledge base documents."""
    __tablename__ = "kb_docs"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    source_type = Column(String(50))  # pdf, article, manual
    source_path = Column(String(1000))
    full_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    chunks = relationship("KBChunk", back_populates="doc", cascade="all, delete-orphan")


class KBChunk(Base):
    """RAG chunks for knowledge base."""
    __tablename__ = "kb_chunks"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey("coach_v2.kb_docs.id", ondelete="CASCADE"), nullable=False)
    
    chunk_index = Column(Integer, nullable=False)
    content = Column(String(2000), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    doc = relationship("KBDoc", back_populates="chunks")


class Note(Base):
    """User notes on activities."""
    __tablename__ = "notes"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    garmin_activity_id = Column(BigInteger, nullable=True)
    
    note_text = Column(String(2000), nullable=False)
    note_type = Column(String(50), default='general')
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PipelineRun(Base):
    """Track pipeline execution."""
    __tablename__ = "pipeline_runs"
    __table_args__ = {'schema': 'coach_v2', 'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    run_type = Column(String(50), nullable=False)  # nightly, manual, incremental
    status = Column(String(20), nullable=False)    # running, completed, failed
    
    activities_processed = Column(Integer, default=0)
    insights_generated = Column(Integer, default=0)
    error_message = Column(Text)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
