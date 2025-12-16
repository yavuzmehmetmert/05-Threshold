"""
Athlete Profile Builder
========================

Builds comprehensive athlete knowledge from historical data:
- Career PRs and milestones
- VO2max/fitness trajectory over time
- Training pattern recognition
- Performance-health correlations
- Seasonal/monthly patterns

This is the "learning" engine that makes the coach truly know the athlete.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import math
import models


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PersonalRecord:
    """Personal Record at a distance."""
    distance_km: float
    distance_label: str  # "5K", "10K", "Half", "Marathon"
    time_seconds: float
    pace_per_km: str
    date: date
    activity_id: int
    activity_name: str
    
    def time_str(self) -> str:
        """Format time as MM:SS or H:MM:SS."""
        hours = int(self.time_seconds // 3600)
        mins = int((self.time_seconds % 3600) // 60)
        secs = int(self.time_seconds % 60)
        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"


@dataclass
class CareerSummary:
    """Lifetime training summary."""
    total_runs: int
    total_distance_km: float
    total_duration_hours: float
    total_elevation_m: float
    first_activity_date: date
    last_activity_date: date
    training_days: int  # Unique days with activity
    
    # PRs at standard distances
    personal_records: Dict[str, PersonalRecord]
    
    # Milestones
    longest_run_km: float
    longest_run_date: date
    highest_weekly_km: float
    highest_monthly_km: float
    
    # Averages
    avg_weekly_km: float
    avg_runs_per_week: float
    consistency_score: int  # 0-100, based on training regularity
    
    def to_brief(self) -> str:
        """Brief summary for prompts."""
        weeks = max(1, (self.last_activity_date - self.first_activity_date).days // 7)
        lines = [
            f"**Kariyer Özeti** ({self.first_activity_date} - {self.last_activity_date})",
            f"- Toplam: {self.total_runs} koşu, {self.total_distance_km:.0f} km",
            f"- Haftalık Ort: {self.avg_weekly_km:.1f} km, {self.avg_runs_per_week:.1f} koşu",
            f"- Tutarlılık: {self.consistency_score}/100",
        ]
        
        if self.personal_records:
            lines.append("**En İyi Süreler (PR):**")
            for label, pr in sorted(self.personal_records.items(), key=lambda x: x[1].distance_km):
                days_ago = (date.today() - pr.date).days
                lines.append(f"- {label}: {pr.time_str()} ({pr.pace_per_km}/km) - {days_ago} gün önce")
        
        return "\n".join(lines)


@dataclass
class FitnessSnapshot:
    """Fitness metrics at a point in time."""
    date: date
    vo2max: Optional[int]
    threshold_pace: Optional[float]  # min/km
    resting_hr: Optional[int]
    weekly_km: float
    weekly_tss: float


@dataclass
class FitnessTrajectory:
    """VO2max and fitness over time."""
    snapshots: List[FitnessSnapshot]
    
    # Calculated trends
    vo2max_start: Optional[int]
    vo2max_current: Optional[int]
    vo2max_change: int
    vo2max_trend: str  # "improving", "declining", "stable", "plateau"
    
    # Key events
    vo2max_peak: Optional[Tuple[date, int]]
    vo2max_low: Optional[Tuple[date, int]]
    
    def trend_description(self) -> str:
        """Human-readable trend description."""
        if self.vo2max_change > 3:
            return f"VO2max {self.vo2max_start} → {self.vo2max_current} (+{self.vo2max_change}), trend: GELİŞİYOR 📈"
        elif self.vo2max_change < -3:
            return f"VO2max {self.vo2max_start} → {self.vo2max_current} ({self.vo2max_change}), trend: DÜŞÜYOR 📉"
        else:
            return f"VO2max {self.vo2max_current}, trend: STABİL ➡️"


@dataclass
class HealthCorrelation:
    """Correlation between health metric and performance."""
    metric_name: str  # "HRV", "Sleep", "Stress"
    correlation_value: float  # -1 to 1
    pattern: str  # Human-readable pattern
    sample_size: int


@dataclass
class TrainingPattern:
    """Detected training pattern."""
    pattern_type: str  # "weekly_structure", "preferred_time", "consistency"
    description: str
    confidence: float


@dataclass
class SeasonSnapshot:
    """Training season summary."""
    period_start: date
    period_end: date
    period_name: str  # "Kış 2024", "Yaz 2024"
    
    # Volume
    total_runs: int
    total_km: float
    avg_weekly_km: float
    
    # Fitness
    vo2max_start: Optional[int]
    vo2max_end: Optional[int]
    vo2max_change: int
    
    # Health averages
    avg_sleep_score: Optional[float]
    avg_hrv: Optional[float]
    avg_stress: Optional[float]
    
    # Key events
    races: List[Dict]
    breakthroughs: List[str]
    
    # AI narrative
    narrative: str


@dataclass
class AthleteProfile:
    """Complete athlete profile with all knowledge layers."""
    user_id: int
    built_at: datetime
    
    # Core layers
    career: CareerSummary
    fitness_trajectory: FitnessTrajectory
    health_correlations: List[HealthCorrelation]
    training_patterns: List[TrainingPattern]
    seasons: List[SeasonSnapshot]
    
    # Current context
    current_weekly_km: float
    current_vo2max: Optional[int]
    current_form_tsb: float
    
    def get_context_for_prompt(self, max_chars: int = 3000) -> str:
        """Build context string for LLM prompts."""
        lines = []
        
        # Career brief
        lines.append(self.career.to_brief())
        
        # Fitness trend
        lines.append(f"\n**Fitness Trendi:**\n{self.fitness_trajectory.trend_description()}")
        
        # Health correlations
        if self.health_correlations:
            lines.append("\n**Bilinen Korelasyonlar:**")
            for corr in self.health_correlations[:3]:
                lines.append(f"- {corr.pattern}")
        
        # Training patterns
        if self.training_patterns:
            lines.append("\n**Antrenman Alışkanlıkları:**")
            for pat in self.training_patterns[:3]:
                lines.append(f"- {pat.description}")
        
        # Current season
        if self.seasons:
            current = self.seasons[0]
            lines.append(f"\n**Bu Sezon ({current.period_name}):**\n{current.narrative}")
        
        result = "\n".join(lines)
        return result[:max_chars]


# =============================================================================
# ATHLETE PROFILE BUILDER
# =============================================================================

class AthleteProfileBuilder:
    """Builds comprehensive athlete profile from database."""
    
    DISTANCE_CATEGORIES = {
        '5K': (4.8, 5.2),
        '10K': (9.5, 10.5),
        'Half': (20.5, 21.5),
        'Marathon': (41.5, 42.5),
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def build_full_profile(self, user_id: int) -> AthleteProfile:
        """Build complete athlete profile with all layers."""
        career = self.build_career_summary(user_id)
        fitness = self.build_fitness_trajectory(user_id, months=12)
        correlations = self.build_health_correlations(user_id, days=90)
        patterns = self.build_training_patterns(user_id)
        seasons = self.build_seasons(user_id, num_seasons=4)
        
        # Current context
        current_week = self._get_current_week_km(user_id)
        current_vo2max = self._get_current_vo2max(user_id)
        current_tsb = self._get_current_tsb(user_id)
        
        return AthleteProfile(
            user_id=user_id,
            built_at=datetime.now(),
            career=career,
            fitness_trajectory=fitness,
            health_correlations=correlations,
            training_patterns=patterns,
            seasons=seasons,
            current_weekly_km=current_week,
            current_vo2max=current_vo2max,
            current_form_tsb=current_tsb
        )
    
    def build_career_summary(self, user_id: int) -> CareerSummary:
        """Build lifetime career summary."""
        # Get all running activities
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.activity_type.ilike('%running%')
        ).order_by(models.Activity.start_time_local.asc()).all()
        
        if not activities:
            return self._empty_career()
        
        # Basic stats
        total_runs = len(activities)
        total_distance = sum((a.distance or 0) / 1000 for a in activities)
        total_duration = sum((a.duration or 0) / 3600 for a in activities)
        total_elevation = sum((a.elevation_gain or 0) for a in activities)
        
        first_date = activities[0].local_start_date
        last_date = activities[-1].local_start_date
        
        # Unique training days
        training_days = len(set(a.local_start_date for a in activities if a.local_start_date))
        
        # Find PRs
        personal_records = self._find_prs(activities)
        
        # Longest run
        longest = max(activities, key=lambda a: a.distance or 0)
        longest_km = (longest.distance or 0) / 1000
        longest_date = longest.local_start_date
        
        # Weekly stats
        weeks_active = max(1, (last_date - first_date).days // 7)
        avg_weekly_km = total_distance / weeks_active
        avg_runs_per_week = total_runs / weeks_active
        
        # Highest week/month
        highest_week = self._get_highest_weekly_km(activities)
        highest_month = self._get_highest_monthly_km(activities)
        
        # Consistency score (0-100)
        expected_days = (last_date - first_date).days
        consistency = min(100, int((training_days / max(1, expected_days / 2)) * 100))
        
        return CareerSummary(
            total_runs=total_runs,
            total_distance_km=total_distance,
            total_duration_hours=total_duration,
            total_elevation_m=total_elevation,
            first_activity_date=first_date,
            last_activity_date=last_date,
            training_days=training_days,
            personal_records=personal_records,
            longest_run_km=longest_km,
            longest_run_date=longest_date,
            highest_weekly_km=highest_week,
            highest_monthly_km=highest_month,
            avg_weekly_km=avg_weekly_km,
            avg_runs_per_week=avg_runs_per_week,
            consistency_score=consistency
        )
    
    def _find_prs(self, activities: List[models.Activity]) -> Dict[str, PersonalRecord]:
        """Find PRs for standard distances."""
        prs = {}
        
        for label, (min_km, max_km) in self.DISTANCE_CATEGORIES.items():
            candidates = [
                a for a in activities
                if a.distance and a.duration
                and min_km <= (a.distance / 1000) <= max_km
            ]
            
            if candidates:
                best = min(candidates, key=lambda a: a.duration)
                dist_km = best.distance / 1000
                pace_sec = best.duration / dist_km
                pace_str = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
                
                prs[label] = PersonalRecord(
                    distance_km=dist_km,
                    distance_label=label,
                    time_seconds=best.duration,
                    pace_per_km=pace_str,
                    date=best.local_start_date,
                    activity_id=best.activity_id,
                    activity_name=best.activity_name or "Unknown"
                )
        
        return prs
    
    def _get_highest_weekly_km(self, activities: List[models.Activity]) -> float:
        """Get highest weekly distance."""
        weekly = {}
        for a in activities:
            if a.local_start_date and a.distance:
                week = a.local_start_date.isocalendar()[:2]
                weekly[week] = weekly.get(week, 0) + (a.distance / 1000)
        return max(weekly.values()) if weekly else 0
    
    def _get_highest_monthly_km(self, activities: List[models.Activity]) -> float:
        """Get highest monthly distance."""
        monthly = {}
        for a in activities:
            if a.local_start_date and a.distance:
                month = (a.local_start_date.year, a.local_start_date.month)
                monthly[month] = monthly.get(month, 0) + (a.distance / 1000)
        return max(monthly.values()) if monthly else 0
    
    def build_fitness_trajectory(self, user_id: int, months: int = 12) -> FitnessTrajectory:
        """Build VO2max and fitness trajectory over time."""
        start_date = date.today() - timedelta(days=months * 30)
        
        # Get VO2max from physiological logs
        physio_logs = self.db.query(models.PhysiologicalLog).filter(
            models.PhysiologicalLog.user_id == user_id,
            models.PhysiologicalLog.calendar_date >= start_date,
            models.PhysiologicalLog.vo2_max.isnot(None)
        ).order_by(models.PhysiologicalLog.calendar_date.asc()).all()
        
        # Get VO2max from activities as fallback
        activities_with_vo2 = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date,
            models.Activity.vo2_max.isnot(None)
        ).order_by(models.Activity.start_time_local.asc()).all()
        
        # Merge VO2max data
        vo2_points = {}
        for log in physio_logs:
            vo2_points[log.calendar_date] = log.vo2_max
        for act in activities_with_vo2:
            if act.local_start_date not in vo2_points:
                vo2_points[act.local_start_date] = act.vo2_max
        
        if not vo2_points:
            return self._empty_trajectory()
        
        # Sort by date
        sorted_points = sorted(vo2_points.items())
        
        # Build snapshots (monthly)
        snapshots = []
        for d, vo2 in sorted_points:
            snapshots.append(FitnessSnapshot(
                date=d,
                vo2max=vo2,
                threshold_pace=None,
                resting_hr=None,
                weekly_km=0,
                weekly_tss=0
            ))
        
        # Calculate trends
        vo2_values = [v for d, v in sorted_points if v]
        vo2_start = vo2_values[0] if vo2_values else None
        vo2_current = vo2_values[-1] if vo2_values else None
        vo2_change = (vo2_current - vo2_start) if (vo2_start and vo2_current) else 0
        
        if vo2_change > 3:
            trend = "improving"
        elif vo2_change < -3:
            trend = "declining"
        elif len(vo2_values) > 5 and max(vo2_values) - min(vo2_values) < 3:
            trend = "plateau"
        else:
            trend = "stable"
        
        # Peak and low
        if vo2_points:
            peak_date = max(vo2_points.items(), key=lambda x: x[1] or 0)
            low_date = min(vo2_points.items(), key=lambda x: x[1] or 999)
        else:
            peak_date = low_date = None
        
        return FitnessTrajectory(
            snapshots=snapshots,
            vo2max_start=vo2_start,
            vo2max_current=vo2_current,
            vo2max_change=vo2_change,
            vo2max_trend=trend,
            vo2max_peak=peak_date,
            vo2max_low=low_date
        )
    
    def build_health_correlations(self, user_id: int, days: int = 90) -> List[HealthCorrelation]:
        """Find correlations between health metrics and performance."""
        correlations = []
        start_date = date.today() - timedelta(days=days)
        
        # Get activities with performance data
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date,
            models.Activity.duration.isnot(None),
            models.Activity.distance.isnot(None)
        ).all()
        
        if len(activities) < 10:
            return correlations
        
        # Build daily performance map (pace as proxy)
        performance = {}
        for a in activities:
            if a.local_start_date and a.distance and a.duration:
                pace = a.duration / (a.distance / 1000)  # sec/km
                if a.local_start_date not in performance or pace < performance[a.local_start_date]:
                    performance[a.local_start_date] = pace
        
        # Get health data
        sleep_logs = {
            s.calendar_date: s.sleep_score
            for s in self.db.query(models.SleepLog).filter(
                models.SleepLog.user_id == user_id,
                models.SleepLog.calendar_date >= start_date
            ).all()
            if s.sleep_score
        }
        
        hrv_logs = {
            h.calendar_date: h.last_night_avg
            for h in self.db.query(models.HRVLog).filter(
                models.HRVLog.user_id == user_id,
                models.HRVLog.calendar_date >= start_date
            ).all()
            if h.last_night_avg
        }
        
        stress_logs = {
            s.calendar_date: s.avg_stress
            for s in self.db.query(models.StressLog).filter(
                models.StressLog.user_id == user_id,
                models.StressLog.calendar_date >= start_date
            ).all()
            if s.avg_stress
        }
        
        # Calculate correlations
        if sleep_logs:
            corr, pattern = self._calc_correlation(sleep_logs, performance, "Uyku")
            if corr is not None:
                correlations.append(HealthCorrelation(
                    metric_name="Sleep",
                    correlation_value=corr,
                    pattern=pattern,
                    sample_size=len(sleep_logs)
                ))
        
        if hrv_logs:
            corr, pattern = self._calc_correlation(hrv_logs, performance, "HRV")
            if corr is not None:
                correlations.append(HealthCorrelation(
                    metric_name="HRV",
                    correlation_value=corr,
                    pattern=pattern,
                    sample_size=len(hrv_logs)
                ))
        
        if stress_logs:
            corr, pattern = self._calc_correlation(stress_logs, performance, "Stres", inverse=True)
            if corr is not None:
                correlations.append(HealthCorrelation(
                    metric_name="Stress",
                    correlation_value=corr,
                    pattern=pattern,
                    sample_size=len(stress_logs)
                ))
        
        return correlations
    
    def _calc_correlation(
        self, 
        health: Dict[date, float], 
        performance: Dict[date, float],
        metric_name: str,
        inverse: bool = False
    ) -> Tuple[Optional[float], str]:
        """Calculate correlation and generate pattern description."""
        # Match dates
        paired = []
        for d, perf in performance.items():
            prev_day = d - timedelta(days=1)
            if prev_day in health:
                paired.append((health[prev_day], perf))
        
        if len(paired) < 5:
            return None, ""
        
        # Simple correlation calculation
        x_vals = [p[0] for p in paired]
        y_vals = [p[1] for p in paired]  # pace (lower = better)
        
        x_mean = sum(x_vals) / len(x_vals)
        y_mean = sum(y_vals) / len(y_vals)
        
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
        den_x = math.sqrt(sum((x - x_mean) ** 2 for x in x_vals))
        den_y = math.sqrt(sum((y - y_mean) ** 2 for y in y_vals))
        
        if den_x * den_y == 0:
            return None, ""
        
        corr = num / (den_x * den_y)
        if inverse:
            corr = -corr  # Stress: high stress = slow pace, but we report positive for bad
        
        # Generate pattern
        if abs(corr) < 0.2:
            pattern = f"{metric_name} ile performans arasında belirgin ilişki yok"
        elif corr > 0.5:
            pattern = f"Yüksek {metric_name} = daha iyi performans (güçlü korelasyon)"
        elif corr > 0.2:
            pattern = f"{metric_name} yüksek olduğunda performans biraz daha iyi"
        elif corr < -0.5:
            pattern = f"Yüksek {metric_name} = kötü performans (güçlü olumsuz etki)"
        else:
            pattern = f"{metric_name} yüksekken performans hafif düşüyor"
        
        return corr, pattern
    
    def build_training_patterns(self, user_id: int) -> List[TrainingPattern]:
        """Detect training patterns and preferences."""
        patterns = []
        
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.activity_type.ilike('%running%')
        ).order_by(models.Activity.start_time_local.desc()).limit(100).all()
        
        if len(activities) < 10:
            return patterns
        
        # Day of week preference
        day_counts = {}
        for a in activities:
            if a.start_time_local:
                day = a.start_time_local.strftime("%A")
                day_counts[day] = day_counts.get(day, 0) + 1
        
        if day_counts:
            fav_day = max(day_counts.items(), key=lambda x: x[1])
            patterns.append(TrainingPattern(
                pattern_type="weekly_structure",
                description=f"En çok {fav_day[0]} günleri koşuyor ({fav_day[1]} koşu)",
                confidence=0.8
            ))
        
        # Time of day preference
        morning = afternoon = evening = 0
        for a in activities:
            if a.start_time_local:
                hour = a.start_time_local.hour
                if hour < 12:
                    morning += 1
                elif hour < 17:
                    afternoon += 1
                else:
                    evening += 1
        
        total = morning + afternoon + evening
        if total > 0:
            if morning > total * 0.6:
                patterns.append(TrainingPattern(
                    pattern_type="preferred_time",
                    description=f"Sabah koşucusu (%{int(morning/total*100)} sabah)",
                    confidence=0.9
                ))
            elif evening > total * 0.6:
                patterns.append(TrainingPattern(
                    pattern_type="preferred_time",
                    description=f"Akşam koşucusu (%{int(evening/total*100)} akşam)",
                    confidence=0.9
                ))
        
        # Long run pattern
        long_runs = [a for a in activities if a.distance and a.distance > 15000]
        if len(long_runs) >= 3:
            long_days = {}
            for a in long_runs:
                if a.start_time_local:
                    day = a.start_time_local.strftime("%A")
                    long_days[day] = long_days.get(day, 0) + 1
            if long_days:
                fav = max(long_days.items(), key=lambda x: x[1])
                patterns.append(TrainingPattern(
                    pattern_type="long_run_day",
                    description=f"Uzun koşular genellikle {fav[0]} günü",
                    confidence=0.7
                ))
        
        return patterns
    
    def build_seasons(self, user_id: int, num_seasons: int = 4) -> List[SeasonSnapshot]:
        """Build seasonal summaries."""
        seasons = []
        today = date.today()
        
        for i in range(num_seasons):
            end_date = today - timedelta(days=i * 90)
            start_date = end_date - timedelta(days=90)
            
            season = self._build_single_season(user_id, start_date, end_date)
            if season.total_runs > 0:
                seasons.append(season)
        
        return seasons
    
    def _build_single_season(self, user_id: int, start: date, end: date) -> SeasonSnapshot:
        """Build a single season snapshot."""
        # Activities in period
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start,
            models.Activity.local_start_date <= end,
            models.Activity.activity_type.ilike('%running%')
        ).all()
        
        total_runs = len(activities)
        total_km = sum((a.distance or 0) / 1000 for a in activities)
        weeks = max(1, (end - start).days // 7)
        avg_weekly = total_km / weeks
        
        # VO2max at start and end
        vo2_start = self._get_vo2max_near_date(user_id, start)
        vo2_end = self._get_vo2max_near_date(user_id, end)
        vo2_change = (vo2_end - vo2_start) if (vo2_start and vo2_end) else 0
        
        # Health averages
        sleep_avg = self._get_avg_sleep(user_id, start, end)
        hrv_avg = self._get_avg_hrv(user_id, start, end)
        stress_avg = self._get_avg_stress(user_id, start, end)
        
        # Season name
        month = start.month
        year = start.year
        if month in [12, 1, 2]:
            season_name = f"Kış {year}"
        elif month in [3, 4, 5]:
            season_name = f"İlkbahar {year}"
        elif month in [6, 7, 8]:
            season_name = f"Yaz {year}"
        else:
            season_name = f"Sonbahar {year}"
        
        # Generate narrative
        narrative = self._generate_season_narrative(
            total_runs, total_km, avg_weekly, vo2_start, vo2_end, 
            sleep_avg, hrv_avg, stress_avg
        )
        
        return SeasonSnapshot(
            period_start=start,
            period_end=end,
            period_name=season_name,
            total_runs=total_runs,
            total_km=total_km,
            avg_weekly_km=avg_weekly,
            vo2max_start=vo2_start,
            vo2max_end=vo2_end,
            vo2max_change=vo2_change,
            avg_sleep_score=sleep_avg,
            avg_hrv=hrv_avg,
            avg_stress=stress_avg,
            races=[],  # TODO: Detect races
            breakthroughs=[],  # TODO: Detect breakthroughs
            narrative=narrative
        )
    
    def _generate_season_narrative(
        self, runs, km, weekly_km, vo2_start, vo2_end, sleep, hrv, stress
    ) -> str:
        """Generate AI-like narrative for a season."""
        parts = []
        
        if runs == 0:
            return "Bu dönemde antrenman kaydı yok."
        
        parts.append(f"{runs} koşu, toplam {km:.0f} km")
        
        if weekly_km > 40:
            parts.append("yüksek hacimli dönem")
        elif weekly_km > 20:
            parts.append("orta hacimli dönem")
        else:
            parts.append("düşük hacimli dönem")
        
        if vo2_start and vo2_end:
            diff = vo2_end - vo2_start
            if diff > 2:
                parts.append(f"VO2max {vo2_start}→{vo2_end} (+{diff}) gelişti")
            elif diff < -2:
                parts.append(f"VO2max {vo2_start}→{vo2_end} ({diff}) geriledi")
        
        if sleep and sleep < 70:
            parts.append("uyku kalitesi düşük")
        if stress and stress > 50:
            parts.append("yüksek stres dönemi")
        
        return ". ".join(parts) + "."
    
    # Helper methods
    def _get_vo2max_near_date(self, user_id: int, target: date) -> Optional[int]:
        """Get VO2max near a date."""
        result = self.db.query(models.Activity.vo2_max).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= target - timedelta(days=14),
            models.Activity.local_start_date <= target + timedelta(days=14),
            models.Activity.vo2_max.isnot(None)
        ).order_by(func.abs(models.Activity.local_start_date - target)).first()
        return result[0] if result else None
    
    def _get_avg_sleep(self, user_id: int, start: date, end: date) -> Optional[float]:
        result = self.db.query(func.avg(models.SleepLog.sleep_score)).filter(
            models.SleepLog.user_id == user_id,
            models.SleepLog.calendar_date >= start,
            models.SleepLog.calendar_date <= end
        ).scalar()
        return round(result, 1) if result else None
    
    def _get_avg_hrv(self, user_id: int, start: date, end: date) -> Optional[float]:
        result = self.db.query(func.avg(models.HRVLog.last_night_avg)).filter(
            models.HRVLog.user_id == user_id,
            models.HRVLog.calendar_date >= start,
            models.HRVLog.calendar_date <= end
        ).scalar()
        return round(result, 1) if result else None
    
    def _get_avg_stress(self, user_id: int, start: date, end: date) -> Optional[float]:
        result = self.db.query(func.avg(models.StressLog.avg_stress)).filter(
            models.StressLog.user_id == user_id,
            models.StressLog.calendar_date >= start,
            models.StressLog.calendar_date <= end
        ).scalar()
        return round(result, 1) if result else None
    
    def _get_current_week_km(self, user_id: int) -> float:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        result = self.db.query(func.sum(models.Activity.distance)).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= week_start
        ).scalar()
        return (result or 0) / 1000
    
    def _get_current_vo2max(self, user_id: int) -> Optional[int]:
        result = self.db.query(models.Activity.vo2_max).filter(
            models.Activity.user_id == user_id,
            models.Activity.vo2_max.isnot(None)
        ).order_by(models.Activity.start_time_local.desc()).first()
        return result[0] if result else None
    
    def _get_current_tsb(self, user_id: int) -> float:
        try:
            import training_load as tl
            activities = self.db.query(models.Activity).filter(
                models.Activity.user_id == user_id
            ).order_by(models.Activity.start_time_local.asc()).all()
            
            act_list = [
                {
                    'local_start_date': a.local_start_date,
                    'start_time_local': a.start_time_local,
                    'duration': a.duration,
                    'average_hr': a.average_hr,
                    'distance': a.distance
                }
                for a in activities
            ]
            pmc = tl.calculate_pmc(act_list, days=365)
            return pmc['tsb']
        except:
            return 0.0
    
    def _empty_career(self) -> CareerSummary:
        return CareerSummary(
            total_runs=0, total_distance_km=0, total_duration_hours=0,
            total_elevation_m=0, first_activity_date=date.today(),
            last_activity_date=date.today(), training_days=0,
            personal_records={}, longest_run_km=0, longest_run_date=date.today(),
            highest_weekly_km=0, highest_monthly_km=0, avg_weekly_km=0,
            avg_runs_per_week=0, consistency_score=0
        )
    
    def _empty_trajectory(self) -> FitnessTrajectory:
        return FitnessTrajectory(
            snapshots=[], vo2max_start=None, vo2max_current=None,
            vo2max_change=0, vo2max_trend="unknown",
            vo2max_peak=None, vo2max_low=None
        )
