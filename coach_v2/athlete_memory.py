"""
Athlete Memory Store
=====================

Multi-layered temporal memory for the coach:
- Career layer (lifetime, rarely changes)
- Seasonal layer (3-month windows, updated weekly)
- Recent layer (last 7 days, updated daily)

This enables the coach to answer questions like:
- "What was my 10K time 7 months ago?"
- "Why was I slow in February?"
- "How have I improved since summer?"
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging

from coach_v2.athlete_profile_builder import (
    AthleteProfileBuilder, 
    AthleteProfile,
    CareerSummary,
    FitnessTrajectory,
    SeasonSnapshot,
    HealthCorrelation,
    TrainingPattern
)


@dataclass
class DailySnapshot:
    """Snapshot of a single day."""
    date: date
    
    # Activity
    has_activity: bool
    activity_name: Optional[str]
    distance_km: float
    duration_min: int
    avg_pace: Optional[str]
    avg_hr: Optional[int]
    
    # Health
    sleep_score: Optional[int]
    hrv: Optional[int]
    stress: Optional[int]
    
    # Context
    notes: str  # AI-generated summary
    
    def to_brief(self) -> str:
        if not self.has_activity:
            return f"{self.date}: Dinlenme günü"
        return f"{self.date}: {self.activity_name or 'Koşu'} - {self.distance_km:.1f}km @ {self.avg_pace}"


@dataclass
class WeeklySnapshot:
    """Snapshot of a week."""
    week_start: date
    week_end: date
    
    # Volume
    total_runs: int
    total_km: float
    total_duration_min: int
    
    # Quality
    avg_pace: Optional[str]
    avg_hr: Optional[int]
    hardest_run: Optional[str]
    
    # Health averages
    avg_sleep: Optional[float]
    avg_hrv: Optional[float]
    avg_stress: Optional[float]
    
    # Context
    summary: str
    
    def to_brief(self) -> str:
        return f"Hafta {self.week_start}: {self.total_runs} koşu, {self.total_km:.0f}km. {self.summary}"


@dataclass
class AthleteMemory:
    """Complete athlete memory with all temporal layers."""
    user_id: int
    last_updated: datetime
    
    # Layer 1: Career (lifetime)
    career: CareerSummary
    
    # Layer 2: Fitness trajectory
    fitness_trajectory: FitnessTrajectory
    
    # Layer 3: Seasonal (last 4 seasons)
    seasons: List[SeasonSnapshot]
    
    # Layer 4: Health correlations
    correlations: List[HealthCorrelation]
    
    # Layer 5: Training patterns
    patterns: List[TrainingPattern]
    
    # Layer 6: Recent weeks (last 4)
    recent_weeks: List[WeeklySnapshot]
    
    # Layer 7: Recent days (last 7)
    recent_days: List[DailySnapshot]
    
    # Meta
    athlete_narrative: str  # AI-generated personality profile
    
    def get_current_week(self) -> Optional[WeeklySnapshot]:
        return self.recent_weeks[0] if self.recent_weeks else None
    
    def get_current_season(self) -> Optional[SeasonSnapshot]:
        return self.seasons[0] if self.seasons else None
    
    def get_today(self) -> Optional[DailySnapshot]:
        today = date.today()
        for d in self.recent_days:
            if d.date == today:
                return d
        return None
    
    def format_known_patterns(self) -> str:
        """Format patterns and correlations for prompts."""
        lines = []
        
        for corr in self.correlations[:3]:
            lines.append(f"- {corr.pattern}")
        
        for pat in self.patterns[:3]:
            lines.append(f"- {pat.description}")
        
        return "\n".join(lines) if lines else "(Henüz yeterli veri yok)"
    
    def get_full_context(self, max_chars: int = 4000) -> str:
        """Build full context for LLM prompts."""
        sections = []
        
        # Career brief
        sections.append("# SENİ TANIYORUM")
        sections.append(self.career.to_brief())
        
        # Fitness trend
        sections.append("\n# FITNESS GELİŞİMİ")
        sections.append(self.fitness_trajectory.trend_description())
        
        # Current season
        if self.seasons:
            s = self.seasons[0]
            sections.append(f"\n# BU SEZON ({s.period_name})")
            sections.append(s.narrative)
        
        # This week
        if self.recent_weeks:
            w = self.recent_weeks[0]
            sections.append(f"\n# BU HAFTA")
            sections.append(w.summary)
        
        # Known patterns
        sections.append("\n# BİLDİĞİM ŞEYLER")
        sections.append(self.format_known_patterns())
        
        # Athlete narrative
        if self.athlete_narrative:
            sections.append(f"\n# SENİN HAKKINDA")
            sections.append(self.athlete_narrative)
        
        result = "\n".join(sections)
        return result[:max_chars]


class AthleteMemoryStore:
    """Manages athlete memory with caching and persistence."""
    
    CACHE_TTL_HOURS = 1  # Refresh memory if older than this
    
    def __init__(self, db: Session):
        self.db = db
        self.profile_builder = AthleteProfileBuilder(db)
        self._cache: Dict[int, AthleteMemory] = {}
    
    def get_memory(self, user_id: int, force_refresh: bool = False) -> AthleteMemory:
        """Get athlete memory, building if needed."""
        # Check cache
        if not force_refresh and user_id in self._cache:
            cached = self._cache[user_id]
            age_hours = (datetime.now() - cached.last_updated).total_seconds() / 3600
            if age_hours < self.CACHE_TTL_HOURS:
                return cached
        
        # Build fresh memory
        memory = self._build_memory(user_id)
        self._cache[user_id] = memory
        
        return memory
    
    def _build_memory(self, user_id: int) -> AthleteMemory:
        """Build complete athlete memory from scratch."""
        logging.info(f"Building athlete memory for user {user_id}")
        
        # Build profile (career, fitness, correlations, patterns, seasons)
        profile = self.profile_builder.build_full_profile(user_id)
        
        # Build recent weeks
        recent_weeks = self._build_recent_weeks(user_id, num_weeks=4)
        
        # Build recent days
        recent_days = self._build_recent_days(user_id, num_days=7)
        
        # Generate athlete narrative
        narrative = self._generate_athlete_narrative(profile)
        
        return AthleteMemory(
            user_id=user_id,
            last_updated=datetime.now(),
            career=profile.career,
            fitness_trajectory=profile.fitness_trajectory,
            seasons=profile.seasons,
            correlations=profile.health_correlations,
            patterns=profile.training_patterns,
            recent_weeks=recent_weeks,
            recent_days=recent_days,
            athlete_narrative=narrative
        )
    
    def _build_recent_weeks(self, user_id: int, num_weeks: int = 4) -> List[WeeklySnapshot]:
        """Build snapshots for recent weeks."""
        import models
        
        weeks = []
        today = date.today()
        
        for i in range(num_weeks):
            week_end = today - timedelta(days=today.weekday() + 7 * i)
            week_start = week_end - timedelta(days=6)
            
            # Get activities for this week
            activities = self.db.query(models.Activity).filter(
                models.Activity.user_id == user_id,
                models.Activity.local_start_date >= week_start,
                models.Activity.local_start_date <= week_end,
                models.Activity.activity_type.ilike('%running%')
            ).all()
            
            total_runs = len(activities)
            total_km = sum((a.distance or 0) / 1000 for a in activities)
            total_min = sum((a.duration or 0) / 60 for a in activities)
            
            # Average pace
            avg_pace = None
            if total_km > 0 and total_min > 0:
                pace_sec = (total_min * 60) / total_km
                avg_pace = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
            
            # Average HR
            hrs = [a.average_hr for a in activities if a.average_hr]
            avg_hr = int(sum(hrs) / len(hrs)) if hrs else None
            
            # Hardest run
            hardest = max(activities, key=lambda a: a.average_hr or 0) if activities else None
            hardest_name = hardest.activity_name if hardest else None
            
            # Health averages
            avg_sleep = self._get_avg_metric(user_id, 'sleep', week_start, week_end)
            avg_hrv = self._get_avg_metric(user_id, 'hrv', week_start, week_end)
            avg_stress = self._get_avg_metric(user_id, 'stress', week_start, week_end)
            
            # Generate summary
            summary = self._generate_week_summary(
                total_runs, total_km, avg_hr, avg_sleep, avg_stress
            )
            
            weeks.append(WeeklySnapshot(
                week_start=week_start,
                week_end=week_end,
                total_runs=total_runs,
                total_km=total_km,
                total_duration_min=int(total_min),
                avg_pace=avg_pace,
                avg_hr=avg_hr,
                hardest_run=hardest_name,
                avg_sleep=avg_sleep,
                avg_hrv=avg_hrv,
                avg_stress=avg_stress,
                summary=summary
            ))
        
        return weeks
    
    def _build_recent_days(self, user_id: int, num_days: int = 7) -> List[DailySnapshot]:
        """Build snapshots for recent days."""
        import models
        
        days = []
        today = date.today()
        
        for i in range(num_days):
            d = today - timedelta(days=i)
            
            # Get activity for this day
            activity = self.db.query(models.Activity).filter(
                models.Activity.user_id == user_id,
                models.Activity.local_start_date == d,
                models.Activity.activity_type.ilike('%running%')
            ).first()
            
            # Get health data
            sleep = self.db.query(models.SleepLog).filter(
                models.SleepLog.user_id == user_id,
                models.SleepLog.calendar_date == d
            ).first()
            
            hrv = self.db.query(models.HRVLog).filter(
                models.HRVLog.user_id == user_id,
                models.HRVLog.calendar_date == d
            ).first()
            
            stress = self.db.query(models.StressLog).filter(
                models.StressLog.user_id == user_id,
                models.StressLog.calendar_date == d
            ).first()
            
            if activity:
                dist = (activity.distance or 0) / 1000
                dur = int((activity.duration or 0) / 60)
                pace = None
                if dist > 0 and dur > 0:
                    pace_sec = (dur * 60) / dist
                    pace = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
                
                days.append(DailySnapshot(
                    date=d,
                    has_activity=True,
                    activity_name=activity.activity_name,
                    distance_km=dist,
                    duration_min=dur,
                    avg_pace=pace,
                    avg_hr=activity.average_hr,
                    sleep_score=sleep.sleep_score if sleep else None,
                    hrv=hrv.last_night_avg if hrv else None,
                    stress=stress.avg_stress if stress else None,
                    notes=f"{activity.activity_name}: {dist:.1f}km"
                ))
            else:
                days.append(DailySnapshot(
                    date=d,
                    has_activity=False,
                    activity_name=None,
                    distance_km=0,
                    duration_min=0,
                    avg_pace=None,
                    avg_hr=None,
                    sleep_score=sleep.sleep_score if sleep else None,
                    hrv=hrv.last_night_avg if hrv else None,
                    stress=stress.avg_stress if stress else None,
                    notes="Dinlenme günü"
                ))
        
        return days
    
    def _get_avg_metric(self, user_id: int, metric: str, start: date, end: date) -> Optional[float]:
        """Get average of a health metric for a date range."""
        import models
        from sqlalchemy import func
        
        if metric == 'sleep':
            result = self.db.query(func.avg(models.SleepLog.sleep_score)).filter(
                models.SleepLog.user_id == user_id,
                models.SleepLog.calendar_date >= start,
                models.SleepLog.calendar_date <= end
            ).scalar()
        elif metric == 'hrv':
            result = self.db.query(func.avg(models.HRVLog.last_night_avg)).filter(
                models.HRVLog.user_id == user_id,
                models.HRVLog.calendar_date >= start,
                models.HRVLog.calendar_date <= end
            ).scalar()
        elif metric == 'stress':
            result = self.db.query(func.avg(models.StressLog.avg_stress)).filter(
                models.StressLog.user_id == user_id,
                models.StressLog.calendar_date >= start,
                models.StressLog.calendar_date <= end
            ).scalar()
        else:
            result = None
        
        return round(result, 1) if result else None
    
    def _generate_week_summary(
        self, runs: int, km: float, hr: Optional[int], 
        sleep: Optional[float], stress: Optional[float]
    ) -> str:
        """Generate AI-like summary for a week."""
        if runs == 0:
            return "Dinlenme haftası."
        
        parts = [f"{runs} koşu, {km:.0f} km"]
        
        if km > 50:
            parts.append("yüksek hacim")
        elif km > 30:
            parts.append("orta hacim")
        else:
            parts.append("düşük hacim")
        
        if hr and hr > 160:
            parts.append("yoğun tempolar")
        
        if sleep and sleep < 70:
            parts.append("uyku kalitesi düşük")
        
        if stress and stress > 50:
            parts.append("stresli dönem")
        
        return ". ".join(parts) + "."
    
    def _generate_athlete_narrative(self, profile: AthleteProfile) -> str:
        """Generate a personality narrative for the athlete."""
        career = profile.career
        
        parts = []
        
        # Experience level
        weeks = max(1, (career.last_activity_date - career.first_activity_date).days // 7)
        if weeks > 100:
            parts.append("Deneyimli bir koşucu")
        elif weeks > 26:
            parts.append("Gelişen bir koşucu")
        else:
            parts.append("Yeni başlayan bir koşucu")
        
        # Volume
        if career.avg_weekly_km > 50:
            parts.append("yüksek hacimli antrenman yapıyor")
        elif career.avg_weekly_km > 25:
            parts.append("düzenli antrenman yapıyor")
        else:
            parts.append("hafif tempoda antrenman yapıyor")
        
        # Consistency
        if career.consistency_score > 70:
            parts.append("Tutarlılığı yüksek")
        elif career.consistency_score < 40:
            parts.append("Düzensiz antrenman alışkanlığı var")
        
        # PRs
        if career.personal_records:
            pr_distances = list(career.personal_records.keys())
            parts.append(f"En aktif mesafeler: {', '.join(pr_distances)}")
        
        # Patterns
        for pat in profile.training_patterns[:2]:
            parts.append(pat.description)
        
        return ". ".join(parts) + "."
    
    def invalidate_cache(self, user_id: int):
        """Force refresh memory on next access."""
        if user_id in self._cache:
            del self._cache[user_id]
