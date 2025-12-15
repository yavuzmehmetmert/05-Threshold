"""
Coach V2 Daily Pipeline
=======================

Nightly job that processes new activities and updates user model.
Can be run manually or via scheduler.
"""

from typing import Optional, List, Dict, Any
from datetime import date, timedelta, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from coach_v2.repository import CoachV2Repository
from coach_v2.summary_builder import SummaryBuilder
from coach_v2.models import PipelineRun
import models


def _to_float(value) -> Optional[float]:
    """Convert Decimal or any numeric to float for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class DailyPipeline:
    """
    Nightly pipeline for processing activities and learning.
    
    Steps:
    1. Find new activities since last run
    2. Build summaries for each
    3. Update user model
    4. Generate insights
    5. (Optional) Generate daily briefing
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = CoachV2Repository(db)
        self.summary_builder = SummaryBuilder(db)
    
    def run(self, user_id: int, force_full: bool = False) -> Dict[str, Any]:
        """
        Run pipeline for a user.
        
        Args:
            user_id: User to process
            force_full: If True, reprocess all activities (not just new ones)
        
        Returns:
            Summary of what was processed
        """
        # Start tracking
        run = self.repo.start_pipeline_run(user_id, 'nightly')
        
        try:
            activities_processed = 0
            insights_generated = 0
            
            # 1. Find and summarize new activities
            since_date = None if force_full else (date.today() - timedelta(days=7))
            new_activities = self.repo.get_unsummarized_activities(user_id, since_date)
            
            for activity in new_activities:
                try:
                    facts_text, summary_text, summary_json, workout_type = \
                        self.summary_builder.build_summary(activity)
                    
                    self.repo.upsert_activity_summary(
                        user_id=user_id,
                        garmin_activity_id=activity.activity_id,
                        facts_text=facts_text,
                        summary_text=summary_text,
                        summary_json=summary_json,
                        local_start_date=activity.local_start_date,
                        workout_type=workout_type
                    )
                    activities_processed += 1
                except Exception as e:
                    # Log but continue
                    print(f"Error summarizing activity {activity.activity_id}: {e}")
            
            # 2. Update user model
            self._update_user_model(user_id)
            
            # 3. Generate insights
            insights = self._generate_insights(user_id)
            insights_generated = len(insights)
            
            # 4. Generate tomorrow's briefing
            self._generate_briefing(user_id, date.today() + timedelta(days=1))
            
            # Mark complete
            self.repo.complete_pipeline_run(
                run,
                activities_processed=activities_processed,
                insights_generated=insights_generated
            )
            
            return {
                'status': 'completed',
                'activities_processed': activities_processed,
                'insights_generated': insights_generated,
                'run_id': run.id
            }
            
        except Exception as e:
            self.repo.complete_pipeline_run(run, error_message=str(e))
            return {
                'status': 'failed',
                'error': str(e),
                'run_id': run.id
            }
    
    def _update_user_model(self, user_id: int):
        """
        Update user model from recent summaries and biometrics.
        
        Model contains:
        - Weekly average km
        - Typical paces per workout type
        - Sleep/HRV patterns
        - Training consistency score
        """
        # Get last 28 days of summaries
        end_date = date.today()
        start_date = end_date - timedelta(days=28)
        summaries = self.repo.get_activity_summaries_range(user_id, start_date, end_date)
        
        if not summaries:
            return
        
        # Calculate aggregates
        total_km = 0
        total_activities = len(summaries)
        workout_counts = {}
        
        for s in summaries:
            if s.summary_json:
                total_km += s.summary_json.get('distance_km', 0)
            if s.workout_type:
                workout_counts[s.workout_type] = workout_counts.get(s.workout_type, 0) + 1
        
        weekly_avg_km = (total_km / 4) if total_km > 0 else 0  # 4 weeks
        
        # Get biometrics
        biometrics = self.repo.get_biometrics_7d(user_id) or {}
        
        # Build model (must be < 4KB)
        model = {
            'weekly_avg_km': round(weekly_avg_km, 1),
            'total_activities_28d': total_activities,
            'workout_distribution': workout_counts,
            'avg_sleep_score': _to_float(biometrics.get('avg_sleep_score')),
            'avg_hrv': _to_float(biometrics.get('avg_hrv')),
            'avg_stress': _to_float(biometrics.get('avg_stress')),
            'training_consistency': self._calculate_consistency(summaries),
            'injury_risk': self._assess_injury_risk(summaries, biometrics),
            'last_updated': str(datetime.utcnow())
        }
        
        self.repo.upsert_user_model(user_id, model)
    
    def _calculate_consistency(self, summaries: List) -> str:
        """Calculate training consistency score."""
        if len(summaries) >= 16:  # 4+ per week
            return 'high'
        elif len(summaries) >= 8:  # 2+ per week
            return 'medium'
        else:
            return 'low'
    
    def _assess_injury_risk(self, summaries: List, biometrics: Dict) -> str:
        """Simple injury risk assessment."""
        # High volume + low HRV + low sleep = high risk
        recent_count = len([s for s in summaries if 
            s.local_start_date >= date.today() - timedelta(days=7)])
        
        if recent_count >= 7:  # Daily running
            if biometrics.get('avg_hrv', 100) < 50:
                return 'high'
            return 'medium'
        
        return 'low'
    
    def _generate_insights(self, user_id: int) -> List:
        """Generate daily insights from patterns."""
        insights = []
        today = date.today()
        
        # Get recent data
        summaries = self.repo.get_activity_summaries_range(
            user_id, 
            today - timedelta(days=7), 
            today
        )
        
        if not summaries:
            return insights
        
        # Insight 1: Volume trend
        total_km = sum(
            s.summary_json.get('distance_km', 0) 
            for s in summaries if s.summary_json
        )
        
        if total_km > 60:
            insight = self.repo.create_insight(
                user_id=user_id,
                insight_date=today,
                insight_text=f"Bu hafta {total_km:.1f} km koştun - yüksek hacim. Dinlenmeyi ihmal etme.",
                evidence_refs={'weekly_km': total_km, 'activity_count': len(summaries)},
                insight_type='trend',
                confidence=0.8
            )
            insights.append(insight)
        
        # Insight 2: Workout variety
        workout_types = set(s.workout_type for s in summaries if s.workout_type)
        if len(workout_types) == 1 and 'easy' not in workout_types:
            insight = self.repo.create_insight(
                user_id=user_id,
                insight_date=today,
                insight_text="Antrenman çeşitliliğin düşük. Farklı tipte çalışmalar ekle.",
                evidence_refs={'workout_types': list(workout_types)},
                insight_type='recommendation',
                confidence=0.7
            )
            insights.append(insight)
        
        return insights
    
    def _generate_briefing(self, user_id: int, briefing_date: date):
        """Generate daily briefing for tomorrow."""
        # Check if already exists
        existing = self.repo.get_briefing(user_id, briefing_date)
        if existing:
            return
        
        # Get context
        user_model = self.repo.get_user_model_json(user_id)
        last_activity = self.repo.get_last_activity_summary(user_id)
        insights = self.repo.get_recent_insights(user_id, days=3)
        
        # Build briefing
        parts = ["Günaydın koşucu! İşte bugünkü özet:"]
        
        if last_activity:
            parts.append(f"\n📊 Son antrenman: {last_activity.summary_text[:200]}")
        
        if user_model:
            weekly_km = user_model.get('weekly_avg_km', 0)
            parts.append(f"\n📈 Haftalık ortalama: {weekly_km:.1f} km")
        
        if insights:
            parts.append("\n💡 Öneriler:")
            for insight in insights[:2]:
                parts.append(f"- {insight.insight_text}")
        
        briefing_text = "\n".join(parts)
        
        self.repo.create_briefing(
            user_id=user_id,
            briefing_date=briefing_date,
            briefing_text=briefing_text,
            sources_json={
                'last_activity': last_activity.garmin_activity_id if last_activity else None,
                'insights_count': len(insights)
            }
        )
