"""
Coach V2 Analysis Pack Generator
================================

Generates rich, LLM-ready context packs for activities.
Includes:
- Structured Facts (compact text)
- Markdown Tables (Laps, Intervals)
- Coach Flags (heuristic detection of issues)
- Derived JSON (for programmatic checks)

Inputs: Activity model, pure raw JSON (Garmin format)
Output: Dictionary matching activity_analysis_packs schema
"""

import json
from datetime import timedelta
import math
from typing import Dict, List, Any, Optional

class AnalysisPackGenerator:
    def __init__(self):
        pass

    def generate_pack(self, activity_row, raw_json: Dict[str, Any]) -> Dict[str, Any]:
        """Generate full analysis pack from activity data."""
        
        # 1. Extract Core Data
        distance_km = (activity_row.distance or 0) / 1000.0
        duration_min = (activity_row.duration or 0) / 60.0
        avg_pace = self._format_pace(activity_row.average_speed)
        avg_hr = int(activity_row.average_hr) if activity_row.average_hr else None
        max_hr = int(activity_row.max_hr) if activity_row.max_hr else None
        
        # 2. Heuristic Checks (The Coach's "Eye")
        flags = []
        if avg_hr and avg_hr > 175:
            flags.append("Very High Avg HR")
        if duration_min > 90 and distance_km < 5:
            flags.append("Low Efficiency (Long duration/Short dist)")
        
        # 3. Generate Facts Text (Compact)
        facts = [
            f"DATE: {activity_row.local_start_date}",
            f"NAME: {activity_row.activity_name}",
            f"TYPE: {activity_row.activity_type}",
            f"DIST: {distance_km:.2f} km",
            f"DUR: {int(duration_min)} min",
            f"PACE: {avg_pace}/km",
            f"HR: Avg {avg_hr} bpm / Max {max_hr} bpm" if avg_hr else "HR: N/A"
        ]
        
        # 4. Process Splits/Laps (Markdown Table)
        laps_table = ""
        laps = raw_json.get('laps', [])
        if laps:
            laps_table = self._generate_laps_table(laps)
            # Check negative split
            if len(laps) > 1:
                first_half = laps[:len(laps)//2]
                second_half = laps[len(laps)//2:]
                avg_pace_1 = sum(l['avgSpeed'] for l in first_half) / len(first_half)
                avg_pace_2 = sum(l['avgSpeed'] for l in second_half) / len(second_half)
                if avg_pace_2 > avg_pace_1: # Higher speed = better
                    flags.append("Negative Split (Paced Well)")
                    facts.append("STRATEGY: Negative Split executed.")
                else:
                    flags.append("Positive Split (Faded)")
        
        # 5. Process Intervals (from splitSummaries if avail)
        # Note: Garmin sometimes puts interval data in lap-like structures
        
        return {
            'user_id': activity_row.user_id,
            'garmin_activity_id': activity_row.activity_id,
            'local_start_date': activity_row.local_start_date,
            'facts_text': "\n".join(facts),
            'tables_markdown': laps_table,
            'flags_json': flags,
            'derived_json': {
                'distance_km': round(distance_km, 2),
                'duration_min': round(duration_min, 1),
                'avg_hr': avg_hr,
                'max_hr': max_hr
            }
        }

    def _generate_laps_table(self, laps: List[Dict]) -> str:
        """Create markdown table for laps."""
        if not laps:
            return ""
            
        rows = []
        rows.append("| Lap | Time | Dist (km) | Pace | Avg HR |")
        rows.append("|-----|------|-----------|------|--------|")
        
        for i, lap in enumerate(laps, 1):
            dist = (lap.get('distance', 0) or 0) / 1000.0
            dur = lap.get('duration', 0) or 0
            if dur == 0: continue
            
            dur_str = str(timedelta(seconds=int(dur)))
            pace = self._format_pace(lap.get('avgSpeed'))
            hr = int(lap.get('avgHeartRate', 0) or 0)
            hr_str = str(hr) if hr > 0 else "-"
            
            rows.append(f"| {i} | {dur_str} | {dist:.2f} | {pace} | {hr_str} |")
            
            if i >= 10: # Cap at 10 laps to save tokens
                rows.append(f"| ... | ... | ... | ... | ... |")
                break
                
        return "\n".join(rows)

    def _format_pace(self, speed_mps):
        """Convert m/s to min:sec/km."""
        if not speed_mps or speed_mps <= 0.1:
            return "-:--"
        pace_sec = 1000.0 / speed_mps
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        return f"{mins}:{secs:02d}"
