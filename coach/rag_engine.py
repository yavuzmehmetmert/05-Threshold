"""
RAG Engine for AI Coach
Retrieval-Augmented Generation with embeddings for efficient context
"""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import date, timedelta
from sqlalchemy.orm import Session
import json
import google.generativeai as genai

import models
from coach.models import CoachUserFacts


@dataclass
class RetrievedContext:
    """Retrieved context for RAG."""
    source: str  # "activity", "knowledge", "user_profile"
    relevance_score: float
    content: str
    metadata: Dict[str, Any]


class RAGEngine:
    """
    Retrieval-Augmented Generation engine.
    Uses embeddings to retrieve only relevant context for each query.
    """
    
    # Intent to retrieval mapping - what to fetch for each query type
    # Intent to retrieval mapping - what to fetch for each query type
    RETRIEVAL_MAP = {
        "interval": ["last_activity_detailed"], # Suppressed workout_patterns for noise reduction
        "performance": ["correlations", "training_load", "biometrics"],
        "sleep": ["sleep_data", "correlations"],
        "hrv": ["hrv_data", "correlations", "recovery"],
        "training": ["training_load", "recent_activities", "user_profile"],
        "goal": ["user_profile", "training_load", "race_history"],
        "injury": ["recent_activities", "training_load", "biometrics"],
        "general": ["user_summary", "last_activity_brief"]
    }
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
    
    def retrieve_for_query(self, query: str) -> Dict[str, Any]:
        """
        Retrieve only relevant context based on query.
        This is the RAG retrieval step - minimal, focused context.
        """
        # Detect query intent
        intent = self._detect_query_intent(query)
        
        # Get retrieval sources for this intent
        sources = self.RETRIEVAL_MAP.get(intent, self.RETRIEVAL_MAP["general"])
        
        context = {}
        
        for source in sources:
            data = self._retrieve_source(source)
            if data:
                context[source] = data
        
        return context
    
    def _detect_query_intent(self, query: str) -> str:
        """Detect query intent for targeted retrieval."""
        query_lower = query.lower()
        
        # Interval/workout specific
        if any(word in query_lower for word in ["interval", "tempo", "set", "tekrar", "8x", "10x", "antrenman yapı"]):
            return "interval"
        
        # Performance/trend analysis
        if any(word in query_lower for word in ["performans", "trend", "gelişim", "ilerleme"]):
            return "performance"
        
        # Sleep related
        if any(word in query_lower for word in ["uyku", "sleep", "dinlen"]):
            return "sleep"
        
        # HRV/recovery
        if any(word in query_lower for word in ["hrv", "toparlan", "recovery"]):
            return "hrv"
        
        # Training advice
        if any(word in query_lower for word in ["antrenman", "program", "plan", "ne yapmalı"]):
            return "training"
        
        # Goals/race
        if any(word in query_lower for word in ["hedef", "yarış", "maraton", "pb"]):
            return "goal"
        
        # Injury
        if any(word in query_lower for word in ["ağrı", "sakatlık", "yaralanma"]):
            return "injury"
        
        return "general"
    
    def _retrieve_source(self, source: str) -> Optional[Any]:
        """Retrieve data from a specific source."""
        
        if source == "last_activity_detailed":
            return self._get_last_activity_json()
        
        elif source == "last_activity_brief":
            return self._get_last_activity_brief()
        
        elif source == "workout_patterns":
            return self._get_workout_patterns()
        
        elif source == "correlations":
            from coach.correlation_engine import CorrelationEngine
            engine = CorrelationEngine(self.db)
            return engine.get_all_correlations(self.user_id, days=30).to_context_string()
        
        elif source == "training_load":
            return self._get_training_load()
        
        elif source == "biometrics":
            return self._get_biometrics_summary()
        
        elif source == "recent_activities":
            return self._get_recent_activities_summary()
        
        elif source == "user_profile":
            return self._get_user_profile()
        
        elif source == "user_summary":
            return self._get_user_summary()
        
        elif source == "sleep_data":
            return self._get_sleep_data()
        
        elif source == "hrv_data":
            return self._get_hrv_data()
        
        return None
    
    def _get_last_activity_json(self) -> Optional[str]:
        """Get last activity as JSON with full details."""
        from coach.activity_analyzer import ActivityAnalyzer
        
        activity = self.db.query(models.Activity).filter(
            models.Activity.user_id == self.user_id
        ).order_by(models.Activity.start_time_local.desc()).first()
        
        if not activity:
            return None
        
        analyzer = ActivityAnalyzer(self.db)
        detailed = analyzer.analyze_activity(self.user_id, activity.id)
        
        if detailed:
            return detailed.to_context_string()
        
        return None
    
    def _get_last_activity_brief(self) -> Optional[str]:
        """Get last activity as brief summary."""
        activity = self.db.query(models.Activity).filter(
            models.Activity.user_id == self.user_id
        ).order_by(models.Activity.start_time_local.desc()).first()
        
        if not activity:
            return None
        
        return json.dumps({
            "date": str(activity.local_start_date),
            "name": activity.activity_name,
            "distance_km": round(activity.distance / 1000, 1) if activity.distance else 0,
            "duration_min": int(activity.duration / 60) if activity.duration else 0,
            "avg_hr": activity.average_hr
        }, ensure_ascii=False)
    
    def _get_workout_patterns(self) -> Optional[str]:
        """Get user's workout patterns from analysis."""
        facts = self.db.query(CoachUserFacts).filter(
            CoachUserFacts.user_id == self.user_id
        ).first()
        
        if facts and facts.facts_summary:
            # Extract just workout pattern section
            return facts.facts_summary[:500]
        
        return None
    
    def _get_training_load(self) -> Optional[str]:
        """Get current training load status."""
        from coach.correlation_engine import CorrelationEngine
        engine = CorrelationEngine(self.db)
        status = engine.get_training_load_status(self.user_id)
        return json.dumps(status, ensure_ascii=False)
    
    def _get_biometrics_summary(self) -> Optional[str]:
        """Get recent biometrics."""
        from coach.correlation_engine import CorrelationEngine
        engine = CorrelationEngine(self.db)
        bio = engine.get_biometric_summary(self.user_id, days=7)
        return json.dumps(bio, ensure_ascii=False)
    
    def _get_recent_activities_summary(self) -> Optional[str]:
        """Get summary of recent activities."""
        start_date = date.today() - timedelta(days=7)
        
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == self.user_id,
            models.Activity.local_start_date >= start_date
        ).order_by(models.Activity.start_time_local.desc()).limit(5).all()
        
        if not activities:
            return None
        
        summary = []
        for a in activities:
            summary.append({
                "date": str(a.local_start_date),
                "km": round(a.distance / 1000, 1) if a.distance else 0,
                "min": int(a.duration / 60) if a.duration else 0
            })
        
        return json.dumps(summary, ensure_ascii=False)
    
    def _get_user_profile(self) -> Optional[str]:
        """Get user profile."""
        user = self.db.query(models.User).filter(
            models.User.id == self.user_id
        ).first()
        
        if not user:
            return None
        
        return json.dumps({
            "name": user.display_name or user.garmin_user_id,
            "weekly_km_target": 60  # Could be from user settings
        }, ensure_ascii=False)
    
    def _get_user_summary(self) -> Optional[str]:
        """Get brief user summary."""
        facts = self.db.query(CoachUserFacts).filter(
            CoachUserFacts.user_id == self.user_id
        ).first()
        
        if facts and facts.facts_summary:
            return facts.facts_summary[:300]
        
        return None
    
    def _get_sleep_data(self) -> Optional[str]:
        """Get recent sleep data."""
        start_date = date.today() - timedelta(days=7)
        
        sleep_logs = self.db.query(models.SleepLog).filter(
            models.SleepLog.user_id == self.user_id,
            models.SleepLog.calendar_date >= start_date
        ).all()
        
        if not sleep_logs:
            return None
        
        data = []
        for s in sleep_logs:
            data.append({
                "date": str(s.calendar_date),
                "hours": round(s.duration_seconds / 3600, 1) if s.duration_seconds else 0,
                "score": s.sleep_score
            })
        
        return json.dumps(data, ensure_ascii=False)
    
    def _get_hrv_data(self) -> Optional[str]:
        """Get recent HRV data."""
        start_date = date.today() - timedelta(days=7)
        
        hrv_logs = self.db.query(models.HRVLog).filter(
            models.HRVLog.user_id == self.user_id,
            models.HRVLog.calendar_date >= start_date
        ).all()
        
        if not hrv_logs:
            return None
        
        data = []
        for h in hrv_logs:
            data.append({
                "date": str(h.calendar_date),
                "hrv": h.last_night_avg,
                "status": h.status
            })
        
        return json.dumps(data, ensure_ascii=False)
