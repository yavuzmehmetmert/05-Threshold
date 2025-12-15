"""
Coach V2 Summary Builder
========================

Generates canonical facts_text and summary_text for activities.
NO LLM calls - pure Python logic.

Key Requirements:
1. facts_text <= 600 chars, BEGIN_FACTS...END_FACTS format
2. summary_text <= 1200 chars, human-readable
3. Interval detection from raw_json.splitSummaries
4. No hallucinated structure when data not present
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal
import json
from sqlalchemy.orm import Session

import models


def _to_float(value) -> float:
    """Convert Decimal or any numeric to float for JSON serialization."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class SummaryBuilder:
    """
    Builds bounded summaries from activity data.
    
    Uses raw_json and activity fields - does NOT query activity_streams
    except in explicit deep analysis mode.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def build_summary(
        self, 
        activity: models.Activity
    ) -> Tuple[str, str, Dict[str, Any], str]:
        """
        Build summary for an activity.
        
        Returns:
            (facts_text, summary_text, summary_json, workout_type)
        """
        # Extract data from activity
        workout_type, structure_info = self._detect_workout_type(activity)
        
        # Build facts_text
        facts_text = self._build_facts_text(activity, workout_type, structure_info)
        
        # Build summary_text
        summary_text = self._build_summary_text(activity, workout_type, structure_info)
        
        # Build summary_json
        summary_json = self._build_summary_json(activity, workout_type, structure_info)
        
        return facts_text, summary_text, summary_json, workout_type
    
    def _detect_workout_type(
        self, 
        activity: models.Activity
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Detect workout type from activity data.
        
        Priority:
        1. raw_json.splitSummaries (Garmin interval data)
        2. Activity duration/pace heuristics
        3. Default to 'unknown'
        
        Returns:
            (workout_type, structure_info dict)
        """
        structure_info = {}
        
        # Try to parse raw_json for Garmin splitSummaries
        if activity.raw_json:
            try:
                raw = activity.raw_json if isinstance(activity.raw_json, dict) else json.loads(activity.raw_json)
                
                if 'splitSummaries' in raw:
                    interval_info = self._parse_split_summaries(raw['splitSummaries'])
                    if interval_info:
                        structure_info = interval_info
                        return ('interval', structure_info)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback: heuristics based on duration and pace
        distance_km = _to_float(activity.distance) / 1000
        duration_min = _to_float(activity.duration) / 60
        
        if duration_min == 0 or distance_km == 0:
            return ('unknown', structure_info)
        
        pace_min_per_km = duration_min / distance_km if distance_km > 0 else 0
        
        # Simple heuristics
        if distance_km >= 15:
            return ('long', structure_info)
        elif duration_min >= 20 and duration_min <= 40:
            # Check for tempo based on HR zones if available
            if activity.average_hr and activity.max_hr:
                hr_pct = activity.average_hr / activity.max_hr
                if 0.80 <= hr_pct <= 0.90:
                    return ('tempo', structure_info)
        
        if pace_min_per_km >= 6.0:
            return ('easy', structure_info)
        
        return ('unknown', structure_info)
    
    def _parse_split_summaries(
        self, 
        split_summaries: list
    ) -> Optional[Dict[str, Any]]:
        """
        Parse Garmin splitSummaries to detect interval structure.
        
        Returns interval info dict if interval detected, None otherwise.
        """
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
        
        if not interval_active:
            return None
        
        # Extract interval details
        num_intervals = interval_active.get('noOfSplits', 0)
        total_duration_sec = interval_active.get('duration', 0)
        total_distance_m = interval_active.get('distance', 0)
        avg_speed_mps = interval_active.get('averageSpeed', 0)
        
        if num_intervals == 0:
            return None
        
        # Calculate per-interval metrics
        duration_per_interval = total_duration_sec / num_intervals if num_intervals > 0 else 0
        
        # Calculate pace (min/km) from speed (m/s)
        if avg_speed_mps > 0:
            pace_min_per_km = 1000 / (avg_speed_mps * 60)
            pace_str = f"{int(pace_min_per_km)}:{int((pace_min_per_km % 1) * 60):02d}"
        else:
            pace_str = "N/A"
        
        # Calculate rest time from recovery splits
        rest_per_interval = 0
        if interval_recovery:
            num_recovery = interval_recovery.get('noOfSplits', 0)
            total_recovery_sec = interval_recovery.get('duration', 0)
            if num_recovery > 0:
                rest_per_interval = int(total_recovery_sec / num_recovery)
        
        # Warmup and cooldown
        warmup_min = 0
        if interval_warmup:
            warmup_min = int(interval_warmup.get('duration', 0) / 60)
        
        cooldown_min = 0
        if interval_cooldown:
            cooldown_min = int(interval_cooldown.get('duration', 0) / 60)
        
        # Build structure string
        interval_duration = int(duration_per_interval)
        if interval_duration < 60:
            interval_str = f"{num_intervals}x{interval_duration}sec @ {pace_str}/km"
        else:
            interval_str = f"{num_intervals}x{interval_duration // 60}min @ {pace_str}/km"
        
        if rest_per_interval > 0:
            interval_str += f", {rest_per_interval}sec rest"
        
        return {
            'num_intervals': num_intervals,
            'interval_structure': interval_str,
            'warmup_min': warmup_min,
            'cooldown_min': cooldown_min,
            'avg_pace': pace_str,
            'rest_sec': rest_per_interval
        }
    
    def _build_facts_text(
        self, 
        activity: models.Activity,
        workout_type: str,
        structure_info: Dict[str, Any]
    ) -> str:
        """
        Build canonical facts_text block.
        MUST be <= 600 chars.
        """
        lines = ["BEGIN_FACTS"]
        
        # Basic info
        lines.append(f"DATE={activity.local_start_date}")
        lines.append(f"NAME={activity.activity_name[:50] if activity.activity_name else 'Activity'}")
        
        distance_km = _to_float(activity.distance) / 1000
        duration_min = int(_to_float(activity.duration) / 60)
        lines.append(f"DISTANCE_KM={distance_km:.1f}")
        lines.append(f"DURATION_MIN={duration_min}")
        
        # Pace
        if distance_km > 0 and duration_min > 0:
            pace = duration_min / distance_km
            pace_str = f"{int(pace)}:{int((pace % 1) * 60):02d}"
            lines.append(f"AVG_PACE={pace_str}/km")
        
        # HR
        if activity.average_hr:
            lines.append(f"AVG_HR={activity.average_hr}")
        if activity.max_hr:
            lines.append(f"MAX_HR={activity.max_hr}")
        
        # Workout type
        lines.append(f"WORKOUT_TYPE={workout_type}")
        
        # Interval structure (if present)
        if workout_type == 'interval' and structure_info.get('interval_structure'):
            lines.append(f"INTERVAL_STRUCTURE={structure_info['interval_structure']}")
            lines.append(f"TOTAL_INTERVALS={structure_info.get('num_intervals', 0)}")
        
        # Warmup/Cooldown (if significant)
        if structure_info.get('warmup_min', 0) > 0:
            lines.append(f"WARMUP_MIN={structure_info['warmup_min']}")
        if structure_info.get('cooldown_min', 0) > 0:
            lines.append(f"COOLDOWN_MIN={structure_info['cooldown_min']}")
        
        # Training effect
        if activity.training_effect:
            lines.append(f"TRAINING_EFFECT={_to_float(activity.training_effect):.1f}")
        
        # Cardiac drift (simplified - would need stream analysis for accurate)
        # For now, estimate from RPE if available
        if activity.rpe:
            lines.append(f"RPE={activity.rpe}")
        
        lines.append("END_FACTS")
        
        facts_text = "\n".join(lines)
        
        # Enforce 600 char limit
        if len(facts_text) > 600:
            # Truncate middle facts, keep essential ones
            essential_lines = ["BEGIN_FACTS"]
            for line in lines[1:-1]:
                if any(key in line for key in ['WORKOUT_TYPE', 'INTERVAL_STRUCTURE', 'DISTANCE_KM', 'AVG_HR']):
                    essential_lines.append(line)
            essential_lines.append("END_FACTS")
            facts_text = "\n".join(essential_lines)
        
        return facts_text[:600]
    
    def _build_summary_text(
        self, 
        activity: models.Activity,
        workout_type: str,
        structure_info: Dict[str, Any]
    ) -> str:
        """
        Build human-readable summary.
        MUST be <= 1200 chars.
        """
        distance_km = _to_float(activity.distance) / 1000
        duration_min = int(_to_float(activity.duration) / 60)
        
        date_str = activity.local_start_date.strftime('%d %b %Y') if activity.local_start_date else 'Unknown date'
        name = activity.activity_name or 'Activity'
        
        parts = []
        
        # Opening line with workout type
        if workout_type == 'interval':
            parts.append(f"{date_str}: {name} - Interval antrenmanı")
        elif workout_type == 'tempo':
            parts.append(f"{date_str}: {name} - Tempo koşusu")
        elif workout_type == 'long':
            parts.append(f"{date_str}: {name} - Uzun koşu")
        elif workout_type == 'easy':
            parts.append(f"{date_str}: {name} - Kolay koşu")
        else:
            parts.append(f"{date_str}: {name}")
        
        # Distance and duration
        parts.append(f"{distance_km:.1f} km, {duration_min} dakika.")
        
        # Structure details
        if structure_info.get('interval_structure'):
            parts.append(f"Yapı: {structure_info['interval_structure']}.")
            if structure_info.get('warmup_min'):
                parts.append(f"Isınma: {structure_info['warmup_min']} dk.")
            if structure_info.get('cooldown_min'):
                parts.append(f"Soğuma: {structure_info['cooldown_min']} dk.")
        
        # HR info
        if activity.average_hr:
            parts.append(f"Ortalama nabız: {activity.average_hr} bpm.")
        
        # Training effect
        if activity.training_effect:
            parts.append(f"Antrenman etkisi: {_to_float(activity.training_effect):.1f}.")
        
        summary = " ".join(parts)
        
        # Enforce 1200 char limit
        return summary[:1200]
    
    def _build_summary_json(
        self, 
        activity: models.Activity,
        workout_type: str,
        structure_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build structured summary for programmatic access."""
        distance_km = _to_float(activity.distance) / 1000
        duration_min = int(_to_float(activity.duration) / 60)
        
        summary = {
            'date': str(activity.local_start_date),
            'name': activity.activity_name,
            'distance_km': round(distance_km, 2),
            'duration_min': duration_min,
            'workout_type': workout_type,
            'avg_hr': int(activity.average_hr) if activity.average_hr else None,
            'max_hr': int(activity.max_hr) if activity.max_hr else None,
            'training_effect': _to_float(activity.training_effect) if activity.training_effect else None,
        }
        
        if structure_info:
            summary['structure'] = structure_info
        
        return summary
