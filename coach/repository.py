"""
Repository Layer for AI Coach
Data access with summary functions that return bounded outputs
Maps to existing tables without knowing exact schema
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

import models
from coach.models import (
    CoachConversationState, 
    CoachUserFacts, 
    CoachBriefing, 
    CoachNote,
    CoachKnowledgeChunk
)
from coach.schemas import (
    UserProfileSummary,
    ActivitySummary,
    RecentSummary,
    ConversationState
)


class CoachRepository:
    """
    Repository for coach data access.
    All methods return bounded, summarized data - NOT raw dumps.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============ User Data ============
    
    def get_user_profile_summary(self, user_id: int) -> Optional[UserProfileSummary]:
        """
        Get compact user profile (~100 chars).
        """
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None
        
        # Calculate age from birth_date if available
        age = None
        if user.birth_date:
            today = date.today()
            age = today.year - user.birth_date.year
            if today.month < user.birth_date.month or (
                today.month == user.birth_date.month and today.day < user.birth_date.day
            ):
                age -= 1
        
        return UserProfileSummary(
            name=user.full_name or "Runner",
            vo2max=user.vo2_max_running,
            resting_hr=user.resting_hr,
            age=age
        )
    
    def get_user_facts(self, user_id: int) -> Optional[CoachUserFacts]:
        """Get AI-extracted user facts."""
        return self.db.query(CoachUserFacts).filter(
            CoachUserFacts.user_id == user_id
        ).first()
    
    def save_user_facts(self, user_id: int, facts: str, preferences: str = "", achievements: str = ""):
        """Save or update user facts."""
        existing = self.get_user_facts(user_id)
        if existing:
            existing.facts_summary = facts
            existing.training_preferences = preferences
            existing.achievements = achievements
            existing.last_analyzed_at = datetime.utcnow()
        else:
            new_facts = CoachUserFacts(
                user_id=user_id,
                facts_summary=facts,
                training_preferences=preferences,
                achievements=achievements,
                last_analyzed_at=datetime.utcnow()
            )
            self.db.add(new_facts)
        self.db.commit()
    
    # ============ Activity Data ============
    
    def get_recent_activity_summaries(
        self, 
        user_id: int, 
        days: int = 7, 
        limit: int = 10
    ) -> List[ActivitySummary]:
        """
        Get compact summaries of recent activities.
        Returns max `limit` activities from last `days` days.
        Each summary is ~150 chars.
        """
        start_date = date.today() - timedelta(days=days)
        
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date
        ).order_by(desc(models.Activity.start_time_local)).limit(limit).all()
        
        summaries = []
        for act in activities:
            summary = ActivitySummary(
                id=act.id,
                date=act.local_start_date.isoformat() if act.local_start_date else "",
                type=act.activity_type or "Running",
                duration_min=int((act.duration or 0) / 60),
                distance_km=round((act.distance or 0) / 1000, 2),
                avg_hr=act.average_hr,
                notes=None  # Could pull from coach_notes if exists
            )
            summaries.append(summary)
        
        return summaries
    
    def get_activity_summary(self, user_id: int, activity_id: int) -> Optional[ActivitySummary]:
        """
        Get compact summary of a specific activity (~150 chars).
        """
        activity = self.db.query(models.Activity).filter(
            models.Activity.id == activity_id,
            models.Activity.user_id == user_id
        ).first()
        
        if not activity:
            return None
        
        return ActivitySummary(
            id=activity.id,
            date=activity.local_start_date.isoformat() if activity.local_start_date else "",
            type=activity.activity_type or "Running",
            duration_min=int((activity.duration or 0) / 60),
            distance_km=round((activity.distance or 0) / 1000, 2),
            avg_hr=activity.average_hr,
            notes=None
        )
    
    def get_recent_summary(self, user_id: int, days: int = 7) -> RecentSummary:
        """
        Get aggregate summary of recent training (~200 chars).
        """
        start_date = date.today() - timedelta(days=days)
        
        # Aggregate query
        result = self.db.query(
            func.count(models.Activity.id).label("count"),
            func.sum(models.Activity.distance).label("total_distance"),
            func.sum(models.Activity.duration).label("total_duration")
        ).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date
        ).first()
        
        return RecentSummary(
            days=days,
            total_activities=result.count or 0,
            total_distance_km=round((result.total_distance or 0) / 1000, 1),
            total_duration_min=int((result.total_duration or 0) / 60),
            avg_tss=None,  # Could calculate if TSS data exists
            trend=None  # Could compare to previous period
        )
    
    def get_last_activity_summary(self, user_id: int) -> Optional[ActivitySummary]:
        """Get summary of the most recent activity."""
        activity = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id
        ).order_by(desc(models.Activity.start_time_local)).first()
        
        if not activity:
            return None
        
        return ActivitySummary(
            id=activity.id,
            date=activity.local_start_date.isoformat() if activity.local_start_date else "",
            type=activity.activity_type or "Running",
            duration_min=int((activity.duration or 0) / 60),
            distance_km=round((activity.distance or 0) / 1000, 2),
            avg_hr=activity.average_hr,
            notes=None
        )
    
    # ============ Conversation State ============
    
    def get_conversation_state(self, user_id: int) -> ConversationState:
        """Get compressed conversation state (~800 chars max)."""
        state = self.db.query(CoachConversationState).filter(
            CoachConversationState.user_id == user_id
        ).first()
        
        if not state:
            return ConversationState()
        
        return ConversationState(
            rolling_summary=state.rolling_summary or "",
            last_user_goal=state.last_user_goal or "",
            last_turns=state.last_turns_compact or [],
            turn_count=state.turn_count or 0
        )
    
    def update_conversation_state(
        self, 
        user_id: int, 
        user_message: str, 
        assistant_response: str,
        new_summary: Optional[str] = None,
        new_goal: Optional[str] = None
    ):
        """
        Update conversation state with new turn.
        Maintains rolling window of last 3 turns.
        """
        state = self.db.query(CoachConversationState).filter(
            CoachConversationState.user_id == user_id
        ).first()
        
        if not state:
            state = CoachConversationState(user_id=user_id)
            self.db.add(state)
        
        # Update last turns (keep last 3)
        turns = state.last_turns_compact or []
        
        # Truncate messages to fit token budget
        user_msg_truncated = user_message[:200] if len(user_message) > 200 else user_message
        asst_msg_truncated = assistant_response[:400] if len(assistant_response) > 400 else assistant_response
        
        turns.append({"role": "user", "msg": user_msg_truncated})
        turns.append({"role": "assistant", "msg": asst_msg_truncated})
        
        # Keep only last 3 turns (6 messages)
        if len(turns) > 6:
            turns = turns[-6:]
        
        state.last_turns_compact = turns
        state.turn_count = (state.turn_count or 0) + 1
        state.last_interaction_at = datetime.utcnow()
        
        if new_summary:
            state.rolling_summary = new_summary[:800]
        if new_goal:
            state.last_user_goal = new_goal[:300]
        
        self.db.commit()
    
    def clear_conversation_state(self, user_id: int):
        """Clear conversation state (start fresh)."""
        self.db.query(CoachConversationState).filter(
            CoachConversationState.user_id == user_id
        ).delete()
        self.db.commit()
    
    # ============ Briefings ============
    
    def get_briefing(self, user_id: int, briefing_date: date) -> Optional[CoachBriefing]:
        """Get cached briefing for a date."""
        return self.db.query(CoachBriefing).filter(
            CoachBriefing.user_id == user_id,
            CoachBriefing.briefing_date == briefing_date
        ).first()
    
    def save_briefing(
        self, 
        user_id: int, 
        briefing_date: date,
        greeting: str,
        training_status: str,
        today_recommendation: str,
        recovery_notes: str = "",
        motivation: str = "",
        full_text: str = "",
        tokens_used: int = 0
    ):
        """Save or update briefing."""
        existing = self.get_briefing(user_id, briefing_date)
        if existing:
            existing.greeting = greeting
            existing.training_status = training_status
            existing.today_recommendation = today_recommendation
            existing.recovery_notes = recovery_notes
            existing.motivation = motivation
            existing.full_text = full_text
            existing.tokens_used = tokens_used
            existing.generated_at = datetime.utcnow()
        else:
            briefing = CoachBriefing(
                user_id=user_id,
                briefing_date=briefing_date,
                greeting=greeting,
                training_status=training_status,
                today_recommendation=today_recommendation,
                recovery_notes=recovery_notes,
                motivation=motivation,
                full_text=full_text,
                tokens_used=tokens_used
            )
            self.db.add(briefing)
        self.db.commit()
    
    # ============ Notes ============
    
    def add_note(
        self, 
        user_id: int, 
        content: str, 
        note_type: str = "general",
        activity_id: Optional[int] = None
    ) -> int:
        """Add a user note and return its ID."""
        note = CoachNote(
            user_id=user_id,
            activity_id=activity_id,
            note_type=note_type,
            content=content[:1000]
        )
        self.db.add(note)
        self.db.commit()
        return note.id
    
    def get_unprocessed_notes(self, user_id: int, limit: int = 10) -> List[CoachNote]:
        """Get notes not yet processed by AI."""
        return self.db.query(CoachNote).filter(
            CoachNote.user_id == user_id,
            CoachNote.processed == False
        ).order_by(CoachNote.created_at).limit(limit).all()
    
    def mark_notes_processed(self, note_ids: List[int]):
        """Mark notes as processed."""
        self.db.query(CoachNote).filter(
            CoachNote.id.in_(note_ids)
        ).update({"processed": True, "processed_at": datetime.utcnow()})
        self.db.commit()
    
    # ============ Training Load Data ============
    
    def get_training_load_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get current training load metrics (CTL, ATL, TSB).
        Returns compact dict for LLM context.
        """
        # This would integrate with existing training_load.py
        # For now, return placeholder that will be mapped
        return {
            "ctl": None,  # Chronic Training Load (Fitness)
            "atl": None,  # Acute Training Load (Fatigue)
            "tsb": None,  # Training Stress Balance (Form)
            "status": "unknown"
        }
    
    # ============ Biometrics ============
    
    def get_recent_biometrics_summary(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get summary of recent biometrics for LLM context.
        Returns compact dict (~200 chars when stringified).
        """
        # This would query sleep_logs, hrv_logs, stress_logs
        # Returning structure that maps to existing tables
        return {
            "avg_sleep_hours": None,
            "avg_hrv": None,
            "avg_stress": None,
            "resting_hr_trend": None
        }
