"""
Coach V2 Repository Layer
=========================

CRUD operations with ENFORCED BOUNDS on all context retrieval.
All methods return bounded data suitable for LLM context.
"""

from typing import Optional, List, Dict, Any
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from coach_v2.models import (
    ActivitySummary, UserModel, Insight, DailyBriefing,
    KBDoc, KBChunk, Note, PipelineRun
)
import models  # Main app models


# ==============================================================================
# BOUNDS CONSTANTS
# ==============================================================================
MAX_FACTS_TEXT_LEN = 600
MAX_SUMMARY_TEXT_LEN = 1200
MAX_USER_MODEL_LEN = 4000
MAX_WEEKLY_TREND_LEN = 800
MAX_RAG_TOTAL_CHARS = 2000
MAX_RAG_TOP_K = 6


class CoachV2Repository:
    """
    Repository for coach_v2 schema with enforced bounds.
    
    All retrieval methods return bounded data.
    All write methods validate bounds before persisting.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================================================
    # ACTIVITY SUMMARY CRUD
    # ==========================================================================
    
    def get_activity_summary(
        self, 
        user_id: int, 
        garmin_activity_id: int
    ) -> Optional[ActivitySummary]:
        """Get bounded summary for a specific activity."""
        return self.db.query(ActivitySummary).filter(
            ActivitySummary.user_id == user_id,
            ActivitySummary.garmin_activity_id == garmin_activity_id
        ).first()
    
    def get_last_activity_summary(self, user_id: int) -> Optional[ActivitySummary]:
        """Get the most recent activity summary for a user."""
        return self.db.query(ActivitySummary).filter(
            ActivitySummary.user_id == user_id
        ).order_by(ActivitySummary.local_start_date.desc()).first()
    
    def get_activity_summaries_range(
        self, 
        user_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[ActivitySummary]:
        """Get all summaries in a date range."""
        return self.db.query(ActivitySummary).filter(
            ActivitySummary.user_id == user_id,
            ActivitySummary.local_start_date >= start_date,
            ActivitySummary.local_start_date <= end_date
        ).order_by(ActivitySummary.local_start_date.desc()).all()
    
    def upsert_activity_summary(
        self,
        user_id: int,
        garmin_activity_id: int,
        facts_text: str,
        summary_text: str,
        summary_json: Dict[str, Any],
        local_start_date: date,
        workout_type: str
    ) -> ActivitySummary:
        """Create or update activity summary with bounds enforcement."""
        # Enforce bounds
        if len(facts_text) > MAX_FACTS_TEXT_LEN:
            facts_text = facts_text[:MAX_FACTS_TEXT_LEN-20] + "\nEND_FACTS"
        if len(summary_text) > MAX_SUMMARY_TEXT_LEN:
            summary_text = summary_text[:MAX_SUMMARY_TEXT_LEN-3] + "..."
        
        existing = self.get_activity_summary(user_id, garmin_activity_id)
        
        if existing:
            existing.facts_text = facts_text
            existing.summary_text = summary_text
            existing.summary_json = summary_json
            existing.workout_type = workout_type
            existing.version += 1
            existing.updated_at = datetime.utcnow()
        else:
            existing = ActivitySummary(
                user_id=user_id,
                garmin_activity_id=garmin_activity_id,
                facts_text=facts_text,
                summary_text=summary_text,
                summary_json=summary_json,
                local_start_date=local_start_date,
                workout_type=workout_type
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        return existing
    
    def get_unsummarized_activities(
        self, 
        user_id: int, 
        since_date: Optional[date] = None
    ) -> List[models.Activity]:
        """Get activities that don't have summaries yet."""
        # Get all activity IDs that already have summaries
        summarized_ids = self.db.query(ActivitySummary.garmin_activity_id).filter(
            ActivitySummary.user_id == user_id
        ).all()
        summarized_ids = [x[0] for x in summarized_ids]
        
        query = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id
        )
        
        if summarized_ids:
            query = query.filter(~models.Activity.activity_id.in_(summarized_ids))
        
        if since_date:
            query = query.filter(models.Activity.local_start_date >= since_date)
        
        return query.order_by(models.Activity.local_start_date.desc()).all()
    
    # ==========================================================================
    # USER MODEL CRUD
    # ==========================================================================
    
    def get_user_model(self, user_id: int) -> Optional[UserModel]:
        """Get the learned user model."""
        return self.db.query(UserModel).filter(
            UserModel.user_id == user_id
        ).first()
    
    def get_user_model_json(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user model as bounded dict."""
        model = self.get_user_model(user_id)
        if model and model.model_json:
            # Ensure bounded
            json_str = json.dumps(model.model_json, ensure_ascii=False)
            if len(json_str) <= MAX_USER_MODEL_LEN:
                return model.model_json
            # If somehow exceeded, return minimal
            return {"error": "model_too_large", "updated_at": str(model.updated_at)}
        return None
    
    def upsert_user_model(
        self, 
        user_id: int, 
        model_json: Dict[str, Any]
    ) -> UserModel:
        """Create or update user model with bounds enforcement."""
        # Enforce bounds
        json_str = json.dumps(model_json, ensure_ascii=False)
        if len(json_str) > MAX_USER_MODEL_LEN:
            raise ValueError(f"model_json exceeds {MAX_USER_MODEL_LEN} chars: {len(json_str)}")
        
        existing = self.get_user_model(user_id)
        
        if existing:
            existing.model_json = model_json
            existing.updated_at = datetime.utcnow()
        else:
            existing = UserModel(
                user_id=user_id,
                model_json=model_json
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        return existing
    
    # ==========================================================================
    # WEEKLY TREND (Computed, Bounded)
    # ==========================================================================
    
    def get_weekly_trend_text(self, user_id: int) -> str:
        """
        Get a bounded weekly trend summary.
        This is backend-computed, not from a table.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        # Get summaries for last 7 days
        summaries = self.get_activity_summaries_range(user_id, start_date, end_date)
        
        if not summaries:
            return "WEEKLY_TREND: no activities in last 7 days"
        
        # Compute aggregates
        total_distance = 0
        total_duration = 0
        workout_types = []
        
        for s in summaries:
            if s.summary_json:
                total_distance += s.summary_json.get('distance_km', 0)
                total_duration += s.summary_json.get('duration_min', 0)
            if s.workout_type:
                workout_types.append(s.workout_type)
        
        # Build bounded trend text
        lines = [
            f"WEEKLY_TREND:",
            f"ACTIVITIES_7D={len(summaries)}",
            f"TOTAL_KM_7D={total_distance:.1f}",
            f"TOTAL_MIN_7D={total_duration}",
            f"WORKOUT_TYPES={','.join(set(workout_types)) or 'unknown'}"
        ]
        
        trend_text = "\n".join(lines)
        
        # Enforce bound
        if len(trend_text) > MAX_WEEKLY_TREND_LEN:
            trend_text = trend_text[:MAX_WEEKLY_TREND_LEN]
        
        return trend_text
    
    # ==========================================================================
    # INSIGHTS CRUD
    # ==========================================================================
    
    def get_recent_insights(
        self, 
        user_id: int, 
        days: int = 7
    ) -> List[Insight]:
        """Get recent active insights."""
        start_date = date.today() - timedelta(days=days)
        return self.db.query(Insight).filter(
            Insight.user_id == user_id,
            Insight.insight_date >= start_date,
            Insight.status == 'active'
        ).order_by(Insight.insight_date.desc()).limit(5).all()
    
    def create_insight(
        self,
        user_id: int,
        insight_date: date,
        insight_text: str,
        evidence_refs: Optional[Dict] = None,
        confidence: float = 0.5,
        insight_type: str = 'recommendation'
    ) -> Insight:
        """Create a new insight with bounds enforcement."""
        if len(insight_text) > 600:
            insight_text = insight_text[:597] + "..."
        
        insight = Insight(
            user_id=user_id,
            insight_date=insight_date,
            insight_text=insight_text,
            evidence_refs=evidence_refs,
            confidence=confidence,
            insight_type=insight_type
        )
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        return insight
    
    # ==========================================================================
    # DAILY BRIEFING CRUD
    # ==========================================================================
    
    def get_briefing(self, user_id: int, briefing_date: date) -> Optional[DailyBriefing]:
        """Get briefing for a specific date."""
        return self.db.query(DailyBriefing).filter(
            DailyBriefing.user_id == user_id,
            DailyBriefing.briefing_date == briefing_date
        ).first()
    
    def create_briefing(
        self,
        user_id: int,
        briefing_date: date,
        briefing_text: str,
        sources_json: Optional[Dict] = None
    ) -> DailyBriefing:
        """Create a daily briefing with bounds enforcement."""
        if len(briefing_text) > 1500:
            briefing_text = briefing_text[:1497] + "..."
        
        briefing = DailyBriefing(
            user_id=user_id,
            briefing_date=briefing_date,
            briefing_text=briefing_text,
            sources_json=sources_json
        )
        self.db.add(briefing)
        self.db.commit()
        self.db.refresh(briefing)
        return briefing
    
    # ==========================================================================
    # RAG RETRIEVAL (Bounded)
    # ==========================================================================
    
    def search_knowledge_base(
        self, 
        query: str, 
        top_k: int = MAX_RAG_TOP_K,
        max_chars: int = MAX_RAG_TOTAL_CHARS
    ) -> List[str]:
        """
        Search knowledge base using full-text search.
        Returns bounded list of chunk contents.
        """
        # Use PostgreSQL full-text search
        sql = text("""
            SELECT content
            FROM coach_v2.kb_chunks
            WHERE content_tsv @@ plainto_tsquery('turkish', :query)
            ORDER BY ts_rank(content_tsv, plainto_tsquery('turkish', :query)) DESC
            LIMIT :top_k
        """)
        
        result = self.db.execute(sql, {"query": query, "top_k": top_k})
        chunks = [row[0] for row in result]
        
        # Enforce total char limit
        selected = []
        total_chars = 0
        for chunk in chunks:
            if total_chars + len(chunk) <= max_chars:
                selected.append(chunk)
                total_chars += len(chunk)
            else:
                # Add partial if room
                remaining = max_chars - total_chars
                if remaining > 100:
                    selected.append(chunk[:remaining] + "...")
                break
        
        return selected
    
    # ==========================================================================
    # NOTES CRUD
    # ==========================================================================
    
    def create_note(
        self,
        user_id: int,
        note_text: str,
        garmin_activity_id: Optional[int] = None,
        note_type: str = 'general'
    ) -> Note:
        """Create a user note."""
        if len(note_text) > 2000:
            note_text = note_text[:1997] + "..."
        
        note = Note(
            user_id=user_id,
            garmin_activity_id=garmin_activity_id,
            note_text=note_text,
            note_type=note_type
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note
    
    # ==========================================================================
    # PIPELINE TRACKING
    # ==========================================================================
    
    def start_pipeline_run(self, user_id: int, run_type: str = 'nightly') -> PipelineRun:
        """Start a new pipeline run."""
        run = PipelineRun(
            user_id=user_id,
            run_type=run_type,
            status='running'
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
    
    def complete_pipeline_run(
        self, 
        run: PipelineRun, 
        activities_processed: int = 0,
        insights_generated: int = 0,
        error_message: Optional[str] = None
    ):
        """Mark pipeline run as complete."""
        run.status = 'failed' if error_message else 'completed'
        run.activities_processed = activities_processed
        run.insights_generated = insights_generated
        run.error_message = error_message
        run.completed_at = datetime.utcnow()
        self.db.commit()
    
    # ==========================================================================
    # PUBLIC TABLE ACCESS (Read-only via view)
    # ==========================================================================
    
    def get_activity_from_view(self, garmin_activity_id: int) -> Optional[Dict]:
        """Get activity data from the v_activities_core view."""
        sql = text("""
            SELECT * FROM coach_v2.v_activities_core
            WHERE garmin_activity_id = :id
        """)
        result = self.db.execute(sql, {"id": garmin_activity_id})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    
    def get_biometrics_7d(self, user_id: int) -> Optional[Dict]:
        """Get 7-day biometrics from view."""
        sql = text("""
            SELECT * FROM coach_v2.v_biometrics_7d
            WHERE user_id = :user_id
        """)
        result = self.db.execute(sql, {"user_id": user_id})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
