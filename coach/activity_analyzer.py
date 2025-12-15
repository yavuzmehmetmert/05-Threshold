"""
Activity Analyzer for AI Coach
Extracts detailed workout intelligence from activity data
"""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

import models


@dataclass
class Interval:
    """Detected interval segment."""
    set_number: int
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    avg_pace_per_km: float  # seconds per km
    avg_hr: int
    max_hr: int
    recovery_seconds: int  # rest after this interval


@dataclass
class WorkoutStructure:
    """Detected workout structure."""
    workout_type: str  # "interval", "tempo", "long_run", "easy", "race", "unknown"
    total_intervals: int
    interval_details: List[Interval]
    warmup_minutes: int
    cooldown_minutes: int
    main_set_summary: str  # e.g. "8x30sec @ 3:20/km, 60sec rest"
    hr_zones_distribution: Dict[str, float]  # Z1-Z5 percentages
    pace_consistency: float  # 0-100 score
    cardiac_drift: float  # % HR increase over time at same pace


@dataclass
class ActivityDetail:
    """Comprehensive activity analysis."""
    id: int
    date: str
    type: str
    name: str
    duration_min: int
    distance_km: float
    avg_hr: int
    max_hr: int
    avg_pace: str  # "5:30/km"
    structure: Optional[WorkoutStructure]
    hr_zones: Dict[str, float]  # time in each zone
    splits: List[Dict[str, Any]]  # per-km splits
    notable_observations: List[str]  # AI-ready insights
    
    def to_context_string(self) -> str:
        """Convert to FACT BLOCK for high LLM salience."""
        # "Red Hammer" approach: Key-Value pairs that stand out
        lines = ["BEGIN_FACTS"]
        lines.append(f"LAST_ACTIVITY_DATE={self.date}")
        lines.append(f"LAST_ACTIVITY_NAME={self.name}")
        lines.append(f"DISTANCE_KM={self.distance_km}")
        lines.append(f"DURATION_MIN={self.duration_min}")
        lines.append(f"AVG_PACE={self.avg_pace}")
        lines.append(f"AVG_HR={self.avg_hr}")
        
        if self.structure:
            lines.append(f"WORKOUT_TYPE={self.structure.workout_type}")
            if self.structure.workout_type == 'interval':
                lines.append(f"INTERVAL_STRUCTURE={self.structure.main_set_summary}")
                lines.append(f"TOTAL_INTERVALS={self.structure.total_intervals}")
            lines.append(f"WARMUP_MIN={self.structure.warmup_minutes}")
            lines.append(f"COOLDOWN_MIN={self.structure.cooldown_minutes}")
            lines.append(f"CARDIAC_DRIFT_PCT={self.structure.cardiac_drift:.1f}")
        
        if self.hr_zones:
             zones_compact = ", ".join([f"Z{k}:{v:.0f}%" for k, v in self.hr_zones.items() if v > 5])
             lines.append(f"HR_ZONES={zones_compact}")
             
        lines.append("END_FACTS")
        return "\n".join(lines)



class ActivityAnalyzer:
    """Analyzes activities for detailed workout intelligence."""
    
    # HR Zone thresholds (% of max HR - will be personalized if user data available)
    DEFAULT_ZONES = {
        1: (0.50, 0.60),   # Recovery
        2: (0.60, 0.70),   # Aerobic Base
        3: (0.70, 0.80),   # Tempo
        4: (0.80, 0.90),   # Threshold
        5: (0.90, 1.00),   # VO2max
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_max_hr(self, user_id: int) -> int:
        """Get or estimate user's max HR."""
        # Check recent activities for max HR
        recent_max = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id
        ).order_by(desc(models.Activity.max_hr)).first()
        
        if recent_max and recent_max.max_hr:
            return recent_max.max_hr
        
        # Fallback: estimate from age if available
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.birth_date:
            age = (datetime.now().date() - user.birth_date).days // 365
            return 220 - age
        
        return 190  # Conservative default
    
    def analyze_activity(self, user_id: int, activity_id: int) -> Optional[ActivityDetail]:
        """Comprehensive analysis of a single activity."""
        activity = self.db.query(models.Activity).filter(
            models.Activity.id == activity_id,
            models.Activity.user_id == user_id
        ).first()
        
        if not activity:
            return None
        
        max_hr = self.get_user_max_hr(user_id)
        
        # Get stream data if available
        streams = self.db.query(models.ActivityStream).filter(
            models.ActivityStream.activity_id == activity.activity_id
        ).order_by(models.ActivityStream.timestamp).all()
        
        # Calculate HR zones distribution
        hr_zones = self._calculate_hr_zones(streams, max_hr) if streams else {}
        
        # Detect workout structure
        structure = self._detect_workout_structure(activity, streams)
        
        # Calculate splits from stream
        splits = self._calculate_km_splits(streams) if streams else []
        
        # Generate notable observations
        observations = self._generate_observations(activity, structure, hr_zones, splits)
        
        # Format avg pace
        avg_pace = self._format_pace(activity.avg_speed) if activity.avg_speed else "--:--"
        
        return ActivityDetail(
            id=activity.id,
            date=activity.local_start_date.isoformat() if activity.local_start_date else "",
            type=activity.activity_type or "Running",
            name=activity.activity_name or "Run",
            duration_min=int((activity.duration or 0) / 60),
            distance_km=round((activity.distance or 0) / 1000, 2),
            avg_hr=activity.average_hr or 0,
            max_hr=activity.max_hr or 0,
            avg_pace=avg_pace,
            structure=structure,
            hr_zones=hr_zones,
            splits=splits,
            notable_observations=observations
        )
    
    def _calculate_hr_zones(self, streams: List, max_hr: int) -> Dict[str, float]:
        """Calculate time in each HR zone."""
        if not streams or max_hr == 0:
            return {}
        
        zone_seconds = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_seconds = 0
        
        for i, stream in enumerate(streams):
            if stream.heart_rate:
                hr_pct = stream.heart_rate / max_hr
                for zone, (low, high) in self.DEFAULT_ZONES.items():
                    if low <= hr_pct < high:
                        zone_seconds[zone] += 1
                        total_seconds += 1
                        break
        
        if total_seconds == 0:
            return {}
        
        return {str(z): (s / total_seconds) * 100 for z, s in zone_seconds.items()}
    
    def _detect_workout_structure(self, activity, streams: List) -> Optional[WorkoutStructure]:
        """Detect if this is intervals, tempo, etc. from Garmin data."""
        # FIRST: Check raw_json for Garmin splitSummaries - this is the most reliable source
        if activity.raw_json:
            try:
                raw = activity.raw_json if isinstance(activity.raw_json, dict) else json.loads(activity.raw_json)
                
                # Check splitSummaries for interval data
                if 'splitSummaries' in raw:
                    structure = self._parse_garmin_splits(raw['splitSummaries'])
                    if structure:
                        # Add cardiac drift from streams
                        structure.cardiac_drift = self._calculate_cardiac_drift(streams)
                        return structure
                
                # Fallback to workoutType
                if 'workoutType' in raw:
                    return self._parse_garmin_workout(raw)
            except:
                pass
        
        # Fallback: detect from stream patterns
        if streams and len(streams) > 60:  # Need at least 1 minute of data
            return self._detect_intervals_from_stream(streams)
        
        # Classify by avg HR zone
        if activity.average_hr and activity.max_hr:
            hr_ratio = activity.average_hr / activity.max_hr
            if hr_ratio < 0.70:
                workout_type = "easy"
            elif hr_ratio < 0.80:
                workout_type = "tempo"
            elif hr_ratio < 0.90:
                workout_type = "threshold"
            else:
                workout_type = "race"
            
            return WorkoutStructure(
                workout_type=workout_type,
                total_intervals=0,
                interval_details=[],
                warmup_minutes=0,
                cooldown_minutes=0,
                main_set_summary="",
                hr_zones_distribution={},
                pace_consistency=0,
                cardiac_drift=self._calculate_cardiac_drift(streams)
            )
        
        return None
    
    def _parse_garmin_splits(self, split_summaries: List[Dict]) -> Optional[WorkoutStructure]:
        """Parse Garmin splitSummaries to detect workout structure."""
        if not split_summaries:
            return None
        
        # Find interval data
        interval_active = None
        interval_warmup = None
        interval_recovery = None
        interval_cooldown = None
        
        for split in split_summaries:
            split_type = split.get('splitType', '')
            if split_type == 'INTERVAL_ACTIVE':
                interval_active = split
            elif split_type == 'INTERVAL_WARMUP':
                interval_warmup = split
            elif split_type == 'INTERVAL_RECOVERY':
                interval_recovery = split
            elif split_type == 'INTERVAL_COOLDOWN':
                interval_cooldown = split
        
        # If we found interval data, this is an interval workout
        if interval_active:
            num_intervals = interval_active.get('noOfSplits', 0)
            total_duration = interval_active.get('duration', 0)
            total_distance = interval_active.get('distance', 0)
            avg_speed = interval_active.get('averageSpeed', 0)
            max_speed = interval_active.get('maxSpeed', 0)
            
            # Calculate per-interval stats
            if num_intervals > 0:
                avg_interval_duration = total_duration / num_intervals
                avg_interval_distance = total_distance / num_intervals
                
                # Format interval duration (could be 30sec, 1min, etc.)
                if avg_interval_duration < 60:
                    duration_str = f"{int(avg_interval_duration)}sec"
                else:
                    duration_str = f"{avg_interval_duration/60:.1f}min"
                
                # Format pace
                if avg_speed > 0:
                    pace_per_km = 1000 / avg_speed
                    pace_min = int(pace_per_km // 60)
                    pace_sec = int(pace_per_km % 60)
                    pace_str = f"{pace_min}:{pace_sec:02d}/km"
                else:
                    pace_str = ""
                
                # Recovery info
                recovery_str = ""
                if interval_recovery:
                    recovery_splits = interval_recovery.get('noOfSplits', 0)
                    recovery_duration = interval_recovery.get('duration', 0)
                    if recovery_splits > 0:
                        avg_recovery = recovery_duration / recovery_splits
                        recovery_str = f", {int(avg_recovery)}sec rest"
                
                # Build main set summary
                main_set = f"{num_intervals}x{duration_str}"
                if pace_str:
                    main_set += f" @ {pace_str}"
                main_set += recovery_str
                
                # Warmup/cooldown
                warmup_min = int(interval_warmup.get('duration', 0) / 60) if interval_warmup else 0
                cooldown_min = int(interval_cooldown.get('duration', 0) / 60) if interval_cooldown else 0
                
                return WorkoutStructure(
                    workout_type="interval",
                    total_intervals=num_intervals,
                    interval_details=[],  # Could populate with detailed per-interval data
                    warmup_minutes=warmup_min,
                    cooldown_minutes=cooldown_min,
                    main_set_summary=main_set,
                    hr_zones_distribution={},
                    pace_consistency=0,
                    cardiac_drift=0  # Will be filled by caller
                )
        
        return None
    
    def _detect_intervals_from_stream(self, streams: List) -> Optional[WorkoutStructure]:
        """Detect interval patterns from speed/HR changes."""
        if len(streams) < 120:  # Need at least 2 minutes
            return WorkoutStructure(
                workout_type="unknown",
                total_intervals=0,
                interval_details=[],
                warmup_minutes=0,
                cooldown_minutes=0,
                main_set_summary="",
                hr_zones_distribution={},
                pace_consistency=0,
                cardiac_drift=0
            )
        
        # Calculate speed changes to find intervals
        speeds = [s.speed for s in streams if s.speed and s.speed > 0]
        if not speeds:
            return None
        
        avg_speed = sum(speeds) / len(speeds)
        high_threshold = avg_speed * 1.15  # 15% above average
        
        # Find high-speed segments (potential intervals)
        intervals = []
        in_interval = False
        interval_start = None
        
        for i, stream in enumerate(streams):
            if stream.speed and stream.speed > high_threshold:
                if not in_interval:
                    in_interval = True
                    interval_start = i
            else:
                if in_interval and interval_start:
                    duration = i - interval_start
                    if 10 < duration < 600:  # 10sec to 10min
                        intervals.append({
                            'start': interval_start,
                            'end': i,
                            'duration': duration
                        })
                in_interval = False
        
        if len(intervals) >= 3:
            # This looks like an interval workout
            avg_duration = sum(i['duration'] for i in intervals) / len(intervals)
            return WorkoutStructure(
                workout_type="interval",
                total_intervals=len(intervals),
                interval_details=[],  # Simplified for now
                warmup_minutes=interval_start // 60 if interval_start else 0,
                cooldown_minutes=0,
                main_set_summary=f"{len(intervals)}x{int(avg_duration)}sec fast",
                hr_zones_distribution={},
                pace_consistency=0,
                cardiac_drift=self._calculate_cardiac_drift(streams)
            )
        
        return WorkoutStructure(
            workout_type="steady",
            total_intervals=0,
            interval_details=[],
            warmup_minutes=0,
            cooldown_minutes=0,
            main_set_summary="",
            hr_zones_distribution={},
            pace_consistency=0,
            cardiac_drift=self._calculate_cardiac_drift(streams)
        )
    
    def _calculate_cardiac_drift(self, streams: List) -> float:
        """Calculate cardiac drift (HR increase at same effort over time)."""
        if not streams or len(streams) < 600:  # Need at least 10 minutes
            return 0.0
        
        # Compare first and last quarter HR
        quarter = len(streams) // 4
        
        first_hr = [s.heart_rate for s in streams[:quarter] if s.heart_rate]
        last_hr = [s.heart_rate for s in streams[-quarter:] if s.heart_rate]
        
        if not first_hr or not last_hr:
            return 0.0
        
        avg_first = sum(first_hr) / len(first_hr)
        avg_last = sum(last_hr) / len(last_hr)
        
        if avg_first == 0:
            return 0.0
        
        return ((avg_last - avg_first) / avg_first) * 100
    
    def _parse_garmin_workout(self, raw_data: dict) -> Optional[WorkoutStructure]:
        """Parse Garmin's workout structure from raw JSON."""
        # TODO: Implement Garmin-specific parsing
        return None
    
    def _calculate_km_splits(self, streams: List) -> List[Dict[str, Any]]:
        """Calculate per-km split times and HR."""
        if not streams:
            return []
        
        splits = []
        current_km = 1
        km_start_idx = 0
        
        # Approximate: 1 stream point ≈ 1 second
        for i, stream in enumerate(streams):
            # Check if we've covered approximately 1km
            # This is simplified - real implementation would track distance
            if i > 0 and i % 300 == 0:  # Every ~5 minutes as proxy
                hr_values = [s.heart_rate for s in streams[km_start_idx:i] if s.heart_rate]
                avg_hr = sum(hr_values) / len(hr_values) if hr_values else 0
                
                splits.append({
                    'km': current_km,
                    'avg_hr': int(avg_hr),
                    'duration_sec': i - km_start_idx
                })
                
                current_km += 1
                km_start_idx = i
        
        return splits[:10]  # Cap at 10 splits for context efficiency
    
    def _generate_observations(
        self, 
        activity, 
        structure: Optional[WorkoutStructure],
        hr_zones: Dict[str, float],
        splits: List
    ) -> List[str]:
        """Generate notable observations for LLM context."""
        observations = []
        
        # Check cardiac drift
        if structure and structure.cardiac_drift > 8:
            observations.append(f"Yüksek cardiac drift ({structure.cardiac_drift:.1f}%) - yorgunluk veya yetersiz hidrasyon?")
        
        # Check zone distribution
        if hr_zones:
            z4_5 = hr_zones.get('4', 0) + hr_zones.get('5', 0)
            if z4_5 > 50:
                observations.append(f"Antrenmanın %{z4_5:.0f}'i yüksek yoğunlukta (Z4-Z5)")
            
            z1_2 = hr_zones.get('1', 0) + hr_zones.get('2', 0)
            if z1_2 > 80:
                observations.append(f"İyi aerobik koşu - %{z1_2:.0f} düşük yoğunluk")
        
        # Check interval structure
        if structure and structure.workout_type == "interval":
            observations.append(f"Interval antrenman tespit edildi: {structure.main_set_summary}")
        
        # Check training effect
        if activity.aerobic_te and activity.aerobic_te > 3.5:
            observations.append(f"Yüksek aerobik etki: {activity.aerobic_te}")
        
        if activity.anaerobic_te and activity.anaerobic_te > 3.0:
            observations.append(f"Anaerobik katkı: {activity.anaerobic_te}")
        
        return observations[:5]  # Max 5 observations
    
    def _format_pace(self, speed_ms: float) -> str:
        """Convert m/s to min:sec/km."""
        if not speed_ms or speed_ms <= 0:
            return "--:--"
        
        pace_seconds_per_km = 1000 / speed_ms
        minutes = int(pace_seconds_per_km // 60)
        seconds = int(pace_seconds_per_km % 60)
        return f"{minutes}:{seconds:02d}"
    
    def get_recent_activities_detailed(
        self, 
        user_id: int, 
        days: int = 7, 
        limit: int = 5
    ) -> List[ActivityDetail]:
        """Get detailed analysis of recent activities."""
        from datetime import date, timedelta
        start_date = date.today() - timedelta(days=days)
        
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date
        ).order_by(desc(models.Activity.start_time_local)).limit(limit).all()
        
        return [
            self.analyze_activity(user_id, a.id) 
            for a in activities 
            if self.analyze_activity(user_id, a.id)
        ]
