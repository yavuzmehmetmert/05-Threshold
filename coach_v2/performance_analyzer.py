"""
Coach V2 Performance Analyzer
==============================

Analyzes user's historical performances to:
1. Find Personal Records (PRs) at different distances
2. Calculate VDOT equivalent
3. Predict race times using Riegel formula
4. Track progression over time
5. Identify strengths and weaknesses

Based on KNOWLEDGE_BASE.md formulas.
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass
import math
from sqlalchemy.orm import Session
import models


@dataclass
class PersonalRecord:
    """Personal Record at a specific distance."""
    distance_km: float
    time_seconds: float
    date: date
    activity_id: int
    activity_name: str
    pace_per_km: str  # "4:42"


@dataclass
class RacePrediction:
    """Predicted race time for a distance."""
    distance_km: float
    predicted_time_seconds: float
    predicted_pace_per_km: str
    confidence: float  # 0-1, based on recency and data quality


@dataclass
class PerformanceProfile:
    """Complete performance profile for a user."""
    personal_records: Dict[str, PersonalRecord]  # "5K", "10K", "Half", "Marathon"
    current_vdot: float
    predicted_times: Dict[str, RacePrediction]
    recent_form_trend: str  # "improving", "stable", "declining"
    strengths: List[str]
    weaknesses: List[str]


class PerformanceAnalyzer:
    """Analyzes user performance history and predicts race times."""
    
    # Standard race distances in km
    RACE_DISTANCES = {
        '5K': 5.0,
        '10K': 10.0,
        'Half': 21.0975,
        'Marathon': 42.195
    }
    
    # Keywords to identify races vs training
    RACE_KEYWORDS = ['race', 'yarış', 'parkrun', 'maraton', 'half', '10k', '5k', 'koşusu']
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_performance_profile(self, user_id: int) -> PerformanceProfile:
        """Build complete performance profile for a user."""
        # Get all activities
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.activity_type.ilike('%running%')
        ).order_by(models.Activity.start_time_local.desc()).all()
        
        # Find PRs
        personal_records = self._find_personal_records(activities)
        
        # Calculate VDOT from best recent performance
        current_vdot = self._calculate_vdot(personal_records)
        
        # Predict times for standard distances
        predicted_times = self._predict_race_times(personal_records, current_vdot)
        
        # Analyze form trend
        form_trend = self._analyze_form_trend(activities, personal_records)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_patterns(activities, personal_records)
        
        return PerformanceProfile(
            personal_records=personal_records,
            current_vdot=current_vdot,
            predicted_times=predicted_times,
            recent_form_trend=form_trend,
            strengths=strengths,
            weaknesses=weaknesses
        )
    
    def _find_personal_records(self, activities: List[models.Activity]) -> Dict[str, PersonalRecord]:
        """Find best performances at standard distances."""
        prs = {}
        
        # Group activities by approximate distance category
        for cat_name, target_km in self.RACE_DISTANCES.items():
            tolerance = 0.3 if target_km <= 10 else 0.5  # km tolerance
            
            best_time = None
            best_activity = None
            
            for a in activities:
                if not a.distance or not a.duration:
                    continue
                
                dist_km = a.distance / 1000
                
                # Check if distance matches this category
                if abs(dist_km - target_km) <= tolerance:
                    # Prioritize actual races
                    is_race = self._is_race(a)
                    
                    if best_time is None or a.duration < best_time:
                        best_time = a.duration
                        best_activity = a
            
            if best_activity:
                pace_sec = best_time / (best_activity.distance / 1000)
                pace_str = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
                
                prs[cat_name] = PersonalRecord(
                    distance_km=best_activity.distance / 1000,
                    time_seconds=best_time,
                    date=best_activity.local_start_date,
                    activity_id=best_activity.activity_id,
                    activity_name=best_activity.activity_name or 'Unknown',
                    pace_per_km=pace_str
                )
        
        return prs
    
    def _is_race(self, activity: models.Activity) -> bool:
        """Check if activity is likely a race."""
        name_lower = (activity.activity_name or '').lower()
        return any(kw in name_lower for kw in self.RACE_KEYWORDS)
    
    def _calculate_vdot(self, prs: Dict[str, PersonalRecord]) -> float:
        """
        Calculate VDOT equivalent from best performance.
        Simplified VDOT calculation based on distance and time.
        """
        if not prs:
            return 0.0
        
        # Use most recent PR for calculation
        # Prefer 5K or 10K as they're most predictive
        best_pr = None
        for dist in ['5K', '10K', 'Half', 'Marathon']:
            if dist in prs:
                if best_pr is None or prs[dist].date > best_pr.date:
                    best_pr = prs[dist]
        
        if not best_pr:
            return 0.0
        
        # Simplified VDOT calculation
        # VDOT ≈ 120 - (time_in_minutes * factor)
        # Factor depends on distance
        time_min = best_pr.time_seconds / 60
        dist = best_pr.distance_km
        
        # Rough VDOT estimation
        # 5K @ 20min ≈ VDOT 45
        # 10K @ 45min ≈ VDOT 42
        if dist <= 6:  # 5K
            vdot = 150 - (time_min * 5.25)
        elif dist <= 12:  # 10K
            vdot = 135 - (time_min * 2.0)
        elif dist <= 25:  # Half
            vdot = 170 - (time_min * 1.2)
        else:  # Marathon
            vdot = 200 - (time_min * 0.65)
        
        return max(25, min(85, vdot))  # Clamp to reasonable range
    
    def _predict_race_times(
        self, 
        prs: Dict[str, PersonalRecord],
        vdot: float
    ) -> Dict[str, RacePrediction]:
        """
        Predict race times using Riegel Formula.
        T2 = T1 × (D2/D1)^1.06
        """
        predictions = {}
        
        if not prs:
            return predictions
        
        # Find best reference PR (prefer recent ones)
        reference_pr = None
        for dist in ['5K', '10K']:  # These are most predictive
            if dist in prs:
                pr = prs[dist]
                # Prefer more recent PRs
                days_old = (date.today() - pr.date).days
                if reference_pr is None or days_old < (date.today() - reference_pr.date).days:
                    reference_pr = pr
        
        if not reference_pr:
            reference_pr = list(prs.values())[0]
        
        # Predict for all standard distances
        for cat_name, target_km in self.RACE_DISTANCES.items():
            if cat_name in prs:
                # Use actual PR
                pr = prs[cat_name]
                pace_sec = pr.time_seconds / pr.distance_km
                pace_str = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
                
                predictions[cat_name] = RacePrediction(
                    distance_km=target_km,
                    predicted_time_seconds=pr.time_seconds,
                    predicted_pace_per_km=pace_str,
                    confidence=1.0  # Actual PR
                )
            else:
                # Predict using Riegel formula
                d1 = reference_pr.distance_km
                t1 = reference_pr.time_seconds
                d2 = target_km
                
                # Riegel: T2 = T1 × (D2/D1)^1.06
                t2 = t1 * ((d2 / d1) ** 1.06)
                
                pace_sec = t2 / d2
                pace_str = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}"
                
                # Confidence decreases with extrapolation distance
                ratio = max(d1, d2) / min(d1, d2)
                confidence = max(0.5, 1.0 - (ratio - 1) * 0.2)
                
                predictions[cat_name] = RacePrediction(
                    distance_km=target_km,
                    predicted_time_seconds=t2,
                    predicted_pace_per_km=pace_str,
                    confidence=confidence
                )
        
        return predictions
    
    def _analyze_form_trend(
        self, 
        activities: List[models.Activity],
        prs: Dict[str, PersonalRecord]
    ) -> str:
        """Analyze if user is improving, stable, or declining."""
        if not prs:
            return "unknown"
        
        # Compare recent performances to PRs
        recent_count = 0
        improving_count = 0
        declining_count = 0
        
        three_months_ago = date.today() - timedelta(days=90)
        six_months_ago = date.today() - timedelta(days=180)
        
        for a in activities[:50]:  # Check last 50 activities
            if not a.distance or not a.duration:
                continue
            
            dist_km = a.distance / 1000
            
            # Find matching PR category
            for cat, target in self.RACE_DISTANCES.items():
                if abs(dist_km - target) <= 0.5 and cat in prs:
                    pr = prs[cat]
                    
                    # Compare pace
                    current_pace = a.duration / dist_km
                    pr_pace = pr.time_seconds / pr.distance_km
                    
                    if a.local_start_date and a.local_start_date >= three_months_ago:
                        recent_count += 1
                        if current_pace < pr_pace * 1.02:  # Within 2% of PR
                            improving_count += 1
                        elif current_pace > pr_pace * 1.10:  # 10% slower
                            declining_count += 1
        
        if recent_count < 3:
            return "insufficient_data"
        
        if improving_count > declining_count * 2:
            return "improving"
        elif declining_count > improving_count * 2:
            return "declining"
        else:
            return "stable"
    
    def _identify_patterns(
        self, 
        activities: List[models.Activity],
        prs: Dict[str, PersonalRecord]
    ) -> Tuple[List[str], List[str]]:
        """Identify user's strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        if not activities:
            return strengths, weaknesses
        
        # Analyze pacing consistency
        pacing_variances = []
        for a in activities[:20]:
            if a.raw_json and 'laps' in a.raw_json:
                laps = a.raw_json['laps']
                if len(laps) >= 3:
                    speeds = [l.get('averageSpeed', 0) for l in laps if l.get('averageSpeed')]
                    if speeds:
                        mean = sum(speeds) / len(speeds)
                        variance = sum((s - mean) ** 2 for s in speeds) / len(speeds)
                        pacing_variances.append(variance / mean if mean > 0 else 0)
        
        if pacing_variances:
            avg_variance = sum(pacing_variances) / len(pacing_variances)
            if avg_variance < 0.02:
                strengths.append("Mükemmel pacing tutarlılığı")
            elif avg_variance > 0.08:
                weaknesses.append("Pacing tutarlılığı geliştirilebilir")
        
        # Analyze HR control
        hr_values = []
        for a in activities[:20]:
            if a.average_hr:
                hr_values.append(a.average_hr)
        
        if hr_values:
            avg_hr = sum(hr_values) / len(hr_values)
            if avg_hr < 155:
                strengths.append("İyi aerobik baz")
            elif avg_hr > 170:
                weaknesses.append("Genellikle çok yoğun koşuyor")
        
        # Check distance preference
        distances = [a.distance / 1000 for a in activities if a.distance]
        if distances:
            avg_dist = sum(distances) / len(distances)
            if avg_dist > 12:
                strengths.append("Dayanıklılık odaklı")
            elif avg_dist < 6:
                strengths.append("Hız odaklı")
        
        return strengths, weaknesses
    
    def format_profile_for_prompt(self, profile: PerformanceProfile) -> str:
        """Format profile as text for LLM prompt."""
        lines = ["# PERFORMANS PROFİLİ"]
        
        # PRs
        lines.append("\n## EN İYİ SÜRELER (PR)")
        for dist, pr in profile.personal_records.items():
            time_str = self._format_time(pr.time_seconds)
            days_ago = (date.today() - pr.date).days
            lines.append(f"- **{dist}**: {time_str} ({pr.pace_per_km}/km) - {pr.date} ({days_ago} gün önce)")
        
        # VDOT
        lines.append(f"\n## VDOT: {profile.current_vdot:.1f}")
        
        # Predictions
        lines.append("\n## TAHMİNİ YARİŞ SÜRELERİ")
        for dist, pred in profile.predicted_times.items():
            time_str = self._format_time(pred.predicted_time_seconds)
            conf = "✓" if pred.confidence >= 0.9 else "~"
            lines.append(f"- {dist}: {time_str} ({pred.predicted_pace_per_km}/km) {conf}")
        
        # Trend
        lines.append(f"\n## FORM TRENDİ: {profile.recent_form_trend.upper()}")
        
        # Strengths/Weaknesses
        if profile.strengths:
            lines.append("\n## GÜÇLÜ YANLAR")
            for s in profile.strengths:
                lines.append(f"- {s}")
        
        if profile.weaknesses:
            lines.append("\n## GELİŞİM ALANLARI")
            for w in profile.weaknesses:
                lines.append(f"- {w}")
        
        return "\n".join(lines)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS or H:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
