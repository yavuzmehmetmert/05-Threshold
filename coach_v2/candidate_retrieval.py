"""
Coach V2 Candidate Retrieval
============================

Fetches activity candidates based on parsed intent.
Uses coach_v2.activity_summaries first, falls back to public.activities.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, func

from coach_v2.models import ActivitySummary
from coach_v2.summary_builder import SummaryBuilder
import models


@dataclass
class ActivityCandidate:
    """A candidate activity for selection."""
    garmin_activity_id: int
    activity_name: str
    local_start_date: date
    distance_km: float
    duration_min: int
    workout_type: Optional[str]
    facts_text: Optional[str]
    summary_text: Optional[str]
    match_score: float = 1.0  # Higher is better


@dataclass
class Resolution:
    """Result of candidate resolution."""
    status: str  # 'selected', 'needs_clarification', 'not_found'
    selected: Optional[ActivityCandidate] = None
    candidates: List[ActivityCandidate] = None
    clarification_message: Optional[str] = None
    
    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []


class CandidateRetriever:
    """Retrieves activity candidates from coach_v2 and public tables."""
    
    def __init__(self, db: Session):
        self.db = db
        self.summary_builder = SummaryBuilder(db)
    
    def get_candidates_by_date(
        self, 
        user_id: int, 
        target_date: date
    ) -> List[ActivityCandidate]:
        """
        Get all activities on a specific date.
        First tries coach_v2.activity_summaries, then falls back to public.activities.
        """
        candidates = []
        
        # 1. Try coach_v2.activity_summaries
        summaries = self.db.query(ActivitySummary).filter(
            ActivitySummary.user_id == user_id,
            ActivitySummary.local_start_date == target_date
        ).all()
        
        if summaries:
            for s in summaries:
                # Get activity name from public.activities
                activity = self.db.query(models.Activity).filter(
                    models.Activity.activity_id == s.garmin_activity_id
                ).first()
                
                name = activity.activity_name if activity else f"Activity {s.garmin_activity_id}"
                distance = s.summary_json.get('distance_km', 0) if s.summary_json else 0
                duration = s.summary_json.get('duration_min', 0) if s.summary_json else 0
                
                candidates.append(ActivityCandidate(
                    garmin_activity_id=s.garmin_activity_id,
                    activity_name=name,
                    local_start_date=s.local_start_date,
                    distance_km=distance,
                    duration_min=duration,
                    workout_type=s.workout_type,
                    facts_text=s.facts_text,
                    summary_text=s.summary_text,
                    match_score=1.0
                ))
        else:
            # 2. Fallback to public.activities
            activities = self.db.query(models.Activity).filter(
                models.Activity.user_id == user_id,
                models.Activity.local_start_date == target_date
            ).all()
            
            for a in activities:
                # Build summary on the fly
                try:
                    facts, summary, summary_json, workout_type = self.summary_builder.build_summary(a)
                except:
                    facts = None
                    summary = None
                    workout_type = 'unknown'
                
                distance = (a.distance or 0) / 1000
                duration = int((a.duration or 0) / 60)
                
                candidates.append(ActivityCandidate(
                    garmin_activity_id=a.activity_id,
                    activity_name=a.activity_name or 'Unknown',
                    local_start_date=a.local_start_date,
                    distance_km=distance,
                    duration_min=duration,
                    workout_type=workout_type,
                    facts_text=facts,
                    summary_text=summary,
                    match_score=0.8  # Lower score for non-summarized
                ))
        
        return candidates
    
    def get_candidates_by_name(
        self, 
        user_id: int, 
        name_query: str,
        target_date: Optional[date] = None,
        date_window_days: int = 90
    ) -> List[ActivityCandidate]:
        """
        Get activities matching a name query using fuzzy matching.
        """
        candidates = []
        name_lower = name_query.lower()
        
        # Define date range
        if target_date:
            start_date = target_date
            end_date = target_date
        else:
            end_date = date.today()
            start_date = end_date - timedelta(days=date_window_days)
        
        # Query activities in date range
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date,
            models.Activity.local_start_date <= end_date
        ).all()
        
        for a in activities:
            if not a.activity_name:
                continue
            
            # Simple fuzzy matching: check if query is in name
            activity_name_lower = a.activity_name.lower()
            
            if name_lower in activity_name_lower or activity_name_lower in name_lower:
                score = 1.0
            elif self._token_overlap(name_lower, activity_name_lower) > 0.5:
                score = 0.7
            else:
                continue
            
            # Get summary if available
            summary = self.db.query(ActivitySummary).filter(
                ActivitySummary.garmin_activity_id == a.activity_id
            ).first()
            
            if summary:
                facts = summary.facts_text
                summary_text = summary.summary_text
                workout_type = summary.workout_type
            else:
                try:
                    facts, summary_text, _, workout_type = self.summary_builder.build_summary(a)
                except:
                    facts = None
                    summary_text = None
                    workout_type = 'unknown'
            
            distance = (a.distance or 0) / 1000
            duration = int((a.duration or 0) / 60)
            
            candidates.append(ActivityCandidate(
                garmin_activity_id=a.activity_id,
                activity_name=a.activity_name,
                local_start_date=a.local_start_date,
                distance_km=distance,
                duration_min=duration,
                workout_type=workout_type,
                facts_text=facts,
                summary_text=summary_text,
                match_score=score
            ))
        
        # Sort by score and date (most recent first for ties)
        candidates.sort(key=lambda c: (-c.match_score, -c.local_start_date.toordinal()))
        
        return candidates[:5]  # Top 5
    
    def get_last_activity(self, user_id: int) -> Optional[ActivityCandidate]:
        """Get the most recent activity for a user."""
        summary = self.db.query(ActivitySummary).filter(
            ActivitySummary.user_id == user_id
        ).order_by(ActivitySummary.local_start_date.desc()).first()
        
        if not summary:
            return None
        
        activity = self.db.query(models.Activity).filter(
            models.Activity.activity_id == summary.garmin_activity_id
        ).first()
        
        name = activity.activity_name if activity else f"Activity {summary.garmin_activity_id}"
        distance = summary.summary_json.get('distance_km', 0) if summary.summary_json else 0
        duration = summary.summary_json.get('duration_min', 0) if summary.summary_json else 0
        
        return ActivityCandidate(
            garmin_activity_id=summary.garmin_activity_id,
            activity_name=name,
            local_start_date=summary.local_start_date,
            distance_km=distance,
            duration_min=duration,
            workout_type=summary.workout_type,
            facts_text=summary.facts_text,
            summary_text=summary.summary_text,
            match_score=1.0
        )
    
    def resolve_candidates(
        self, 
        candidates: List[ActivityCandidate],
        name_hint: Optional[str] = None
    ) -> Resolution:
        """
        Resolve candidates to a single selection or request clarification.
        """
        if not candidates:
            return Resolution(
                status='not_found',
                clarification_message="Bu tarih veya isimle eşleşen aktivite bulamadım. Lütfen tarih (örn: 9 mart 2025) veya aktivite ismini belirt."
            )
        
        if len(candidates) == 1:
            return Resolution(
                status='selected',
                selected=candidates[0]
            )
        
        # Multiple candidates - need clarification
        # If we have a name hint, try to narrow down
        if name_hint:
            name_lower = name_hint.lower()
            exact_matches = [c for c in candidates if name_lower in c.activity_name.lower()]
            if len(exact_matches) == 1:
                return Resolution(
                    status='selected',
                    selected=exact_matches[0]
                )
        
        # Build clarification message
        lines = ["Bu kriterlere uyan birden fazla aktivite buldum:"]
        for i, c in enumerate(candidates[:5], 1):
            lines.append(f"{i}) {c.local_start_date} — {c.activity_name} — {c.distance_km:.1f} km — {c.duration_min} dk")
        lines.append("\nHangisini soruyorsun?")
        
        return Resolution(
            status='needs_clarification',
            candidates=candidates[:5],
            clarification_message="\n".join(lines)
        )
    
    def _token_overlap(self, s1: str, s2: str) -> float:
        """Calculate token overlap ratio."""
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union)
