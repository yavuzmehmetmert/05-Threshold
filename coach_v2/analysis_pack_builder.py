"""
Coach V2 Analysis Pack Builder
==============================

Deterministic builder that converts diverse Activity Details JSON into a strictly bounded 
"Analysis Pack" for the LLM. 

This is the single source of truth for what the Coach knows about an activity.
It abstracts away JSON structure variations and guarantees consistent context.

Structure:
1. FACTS: Flat key-value pairs (max 900 chars)
2. TABLES: Markdown tables (Laps, Technique)
3. FLAGS: Deterministic heuristic flags
4. READINESS: Sleep, HRV, Stress context
5. OPTIONAL_RAW_POINTERS: Paths to raw data (internal use)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class AnalysisPackBuilder:
    def __init__(self):
        pass

    def build_pack(self, activity_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds a complete Analysis Pack from activity details JSON.
        
        Args:
            activity_details: The full JSON payload from frontend/DB.
        
        Returns:
            Dict containing bounded text sections for LLM consumption.
        """
        
        # 1. Build Sections
        facts_text = self._build_facts(activity_details)
        tables_md = self._build_tables(activity_details)
        flags_list = self._build_flags(activity_details)
        readiness_text = self._build_readiness(activity_details)
        
        # 2. Assemble Pack
        return {
            "facts": facts_text,
            "tables": tables_md,
            "flags": flags_list,
            "readiness": readiness_text
        }

    def _build_facts(self, data: Dict[str, Any]) -> str:
        """Construct compact key-value facts."""
        lines = []
        
        # Identity
        lines.append(f"ACTIVITY_NAME: {data.get('activityName', 'Unknown')}")
        lines.append(f"TYPE: {data.get('activityType', {}).get('typeKey', 'running')}")
        lines.append(f"START_TIME: {data.get('startTimeLocal', 'N/A')}")
        
        # Core Metrics
        summary = data.get('summaryDTO', {})
        dist = summary.get('distance')  # usually meters
        dur = summary.get('duration')   # seconds
        
        if dist: lines.append(f"DISTANCE: {dist/1000:.2f} km")
        if dur: lines.append(f"DURATION: {int(dur/60)} min")
        
        # Pace
        avg_speed = summary.get('averageSpeed')
        if avg_speed:
            lines.append(f"AVG_PACE: {self._format_pace(avg_speed)}/km")
            
        # HR
        avg_hr = summary.get('averageHR')
        max_hr = summary.get('maxHR')
        if avg_hr: lines.append(f"AVG_HR: {int(avg_hr)}")
        if max_hr: lines.append(f"MAX_HR: {int(max_hr)}")
        
        # Power / Elev / Cal
        avg_power = summary.get('averagePower')
        if avg_power: lines.append(f"AVG_POWER: {int(avg_power)} W")
        
        elev_gain = summary.get('elevationGain')
        if elev_gain: lines.append(f"ELEV_GAIN: {int(elev_gain)} m")
        
        calories = summary.get('calories')
        if calories: lines.append(f"CALORIES: {int(calories)}")
        
        # Technical
        cadence = summary.get('averageRunningCadenceInStepsPerMinute')
        if cadence: lines.append(f"AVG_CADENCE: {int(cadence)} spm")
        
        gct = summary.get('averageGroundContactTime')
        if gct: lines.append(f"AVG_GCT: {int(gct)} ms")
        
        vo = summary.get('averageVerticalOscillation')
        if vo: lines.append(f"AVG_VERT_OSC: {vo:.1f} cm")
        
        stride = summary.get('averageStrideLength')
        if stride: lines.append(f"AVG_STRIDE: {stride/100:.2f} m" if stride > 10 else f"AVG_STRIDE: {stride:.2f} m")

        # Weather (often separated or in metadata)
        weather = data.get('weather', {})
        if not weather:
             # Try nested location-based structure if strictly garmin response
             weather = data.get('metadataDTO', {}).get('weather', {})
             
        if weather:
             temp = weather.get('temperature')
             hum = weather.get('relativeHumidity')
             wind = weather.get('windSpeed')
             if temp: lines.append(f"WEATHER_TEMP: {temp} C")
             if hum: lines.append(f"HUMIDITY: {hum} %")
             if wind: lines.append(f"WIND: {wind} km/h")

        return "\n".join(lines[:25]) # Cap length logic implicit

    def _build_tables(self, data: Dict[str, Any]) -> str:
        """Create markdown tables for Laps and Technique."""
        laps = data.get('laps', [])
        if not laps:
            return "No Lap Data Available"
            
        # Table A: Laps (Top 10 max)
        # Columns: Lap #, Time, Dist, Pace, HR, Max HR
        headers = "| # | Time | Dist | Pace | HR | Max HR |"
        sep = "|---|---|---|---|---|---|"
        rows = [headers, sep]
        
        for i, lap in enumerate(laps[:10], 1):
            dur = lap.get('duration', 0)
            dist = lap.get('distance', 0)
            
            # Formatting
            dur_str = str(timedelta(seconds=int(dur))) if dur else "-"
            dist_str = f"{dist/1000:.2f}" if dist else "-"
            pace_str = self._format_pace(lap.get('averageSpeed'))
            hr_str = str(int(lap.get('averageHR'))) if lap.get('averageHR') else "-"
            max_hr_str = str(int(lap.get('maxHR'))) if lap.get('maxHR') else "-"
            
            rows.append(f"| {i} | {dur_str} | {dist_str} | {pace_str} | {hr_str} | {max_hr_str} |")
            
        if len(laps) > 10:
            rows.append(f"| ... | ... | ... | ... | ... | ... |")
            
        return "\n".join(rows)

    def _build_flags(self, data: Dict[str, Any]) -> List[str]:
        """Heuristic flags based on data."""
        flags = []
        summary = data.get('summaryDTO', {})
        laps = data.get('laps', [])
        
        # 0. Data Consistency Check (RPE vs HR)
        # Assuming RPE might come from metadata or description if not in summaryDTO standard field
        # Use simple heuristic: if Avg HR > 170 (Zone 4/5) implies RPE > 7
        avg_hr = summary.get('averageHR')
        if avg_hr and avg_hr > 175:
             # This is a hard effort.
             flags.append("Intensity: High Zone 4/5 effort detected (Avg HR > 175).")
        
        # ... (Flags logic)
        
        # 1. Cardiac Drift Check (Enriched)
        if len(laps) >= 4:
            mid = len(laps) // 2
            first_half_hr = sum(l.get('averageHR', 0) for l in laps[:mid]) / mid
            second_half_hr = sum(l.get('averageHR', 0) for l in laps[mid:]) / (len(laps) - mid)
            if second_half_hr > first_half_hr * 1.05:
                drift_amt = int(second_half_hr - first_half_hr)
                flags.append(f"Cardiac Drift Detected: +{drift_amt} bpm in second half. (Likely causes: Dehydration, Overheating, or lack of Aerobic Base).")

        # 2. PROGRESSION RUN DETECTION
        # Look for: warmup -> speed increasing -> cooldown pattern
        if len(laps) >= 5:
            speeds = [l.get('averageSpeed', 0) for l in laps if l.get('averageSpeed', 0) > 0]
            if len(speeds) >= 5:
                # Check for progression pattern
                # Skip first 2-3 (warmup) and last 2-3 (cooldown), check middle increases
                warmup_laps = 2  # Assume 2-3km warmup
                cooldown_laps = 2  # Assume 2-3km cooldown
                
                if len(speeds) > warmup_laps + cooldown_laps + 2:
                    main_speeds = speeds[warmup_laps:-cooldown_laps]
                    
                    # Check if speeds are generally increasing
                    increasing_count = 0
                    for i in range(1, len(main_speeds)):
                        if main_speeds[i] > main_speeds[i-1] * 0.98:  # Allow small variance
                            increasing_count += 1
                    
                    progression_ratio = increasing_count / (len(main_speeds) - 1) if len(main_speeds) > 1 else 0
                    
                    if progression_ratio >= 0.6:  # 60%+ laps increasing
                        first_pace = self._format_pace(main_speeds[0])
                        last_pace = self._format_pace(main_speeds[-1])
                        flags.append(f"PROGRESSION RUN: Detected build-up pattern ({first_pace} → {last_pace}). Great negative split execution!")
                    
                    # Also check for gradual build in warmup phase
                    warmup_speeds = speeds[:warmup_laps+1] if len(speeds) > warmup_laps else []
                    cooldown_speeds = speeds[-cooldown_laps:] if len(speeds) > cooldown_laps else []
                    
                    if warmup_speeds and cooldown_speeds:
                        avg_warmup = sum(warmup_speeds) / len(warmup_speeds)
                        avg_cooldown = sum(cooldown_speeds) / len(cooldown_speeds)
                        avg_main = sum(main_speeds) / len(main_speeds) if main_speeds else 0
                        
                        # Warmup slower than main, cooldown slower than main = structured run
                        if avg_warmup < avg_main * 0.95 and avg_cooldown < avg_main * 0.95:
                            flags.append("STRUCTURED WORKOUT: Clear warmup/main/cooldown phases detected. Proper session structure!")

        # ... (Negative Split)

        # 6. Grey Zone Detection (Enriched)
        max_hr = summary.get('maxHR')
        if avg_hr and max_hr:
            z3_low = max_hr * 0.70
            z3_high = max_hr * 0.83
            if z3_low < avg_hr < z3_high and summary.get('duration', 0) > 1800:
                flags.append("Zone 3 Warning: 'Grey Zone' training detected. (Cause: 'Ego Running' or lack of discipline? Too hard for recovery, too easy for gains).")
        elif avg_hr and 148 < avg_hr < 162: # Fallback heuristic
            flags.append("Zone 3 Warning: HR indicates potential 'Grey Zone' (148-162 bpm). (Risk: Accumulating fatigue without specific adaptation).")


        # 7. Short Run / Junk Mile Check
        # If run is < 30 mins, < 5km, and not explicitly "Recovery"
        dist_m = summary.get('distance', 0)
        dur_s = summary.get('duration', 0)
        if 0 < dur_s < 1800 and dist_m < 4000:
            flags.append("Volume Alert: Very short duration (<30 mins). Ensure this is intentional recovery or shakeout.")

        # 8. Recovery vs Intensity Matrix (Enriched)
        readiness = data.get('readinessDTO', {})
        sleep_score = readiness.get('sleepScore')
        
        if sleep_score and sleep_score < 50:
            if any("High Zone 4/5" in f for f in flags) or avg_hr > 170:
                 flags.append("DANGER ZONE: High Intensity effort on Poor Sleep (<50). (Risk: High Cortisol, delayed recovery, injury prone).")
            else:
                 flags.append("Smart Training: Low intensity maintained during poor recovery day. (Benefit: Active recovery without autonomic stress).")

        # 9. Pacing Variance (Enriched)
        # Calculate standard deviation of lap paces if we have enough laps
        if len(laps) >= 4:
             speeds = [l.get('averageSpeed', 0) for l in laps]
             valid_speeds = [s for s in speeds if s > 0]
             if valid_speeds:
                 mean_speed = sum(valid_speeds) / len(valid_speeds)
                 variance = sum((s - mean_speed) ** 2 for s in valid_speeds) / len(valid_speeds)
                 std_dev = variance ** 0.5
                 # CV (Coefficient of Variation)
                 cv = std_dev / mean_speed
                 if cv < 0.02: 
                     flags.append(f"Pacing: METRONOME ({cv*100:.1f}% var). (Insight: Excellent neuromuscular control and effort management).")
                 elif cv > 0.10: 
                     flags.append(f"Pacing: ERRATIC ({cv*100:.1f}% var). (Cause: Lack of focus, terrain changes, or starting too fast).")

        return flags

    def _build_readiness(self, data: Dict[str, Any]) -> str:
        """Extract sleep/readiness data if present in payload."""
        # This assumes the payload MIGHT be enriched with readiness data 
        # OR we might need to rely on separate fetch in orchestration.
        # IF the frontend sends it (as requested), we parse it here.
        
        # Example structure expectation: data['readiness'] or data['wellness']
        readiness = data.get('readinessDTO', {}) 
        if not readiness:
            # Fallback checks
            return "READINESS DATA: Not included in this activity payload."
            
        lines = []
        sleep_score = readiness.get('sleepScore')
        sleep_sec = readiness.get('sleepDurationSeconds')
        hrv = readiness.get('hrvLastNightAvg')
        
        if sleep_score is not None: lines.append(f"SLEEP_SCORE: {sleep_score}")
        if sleep_sec: 
            hours = sleep_sec / 3600
            lines.append(f"SLEEP_DURATION: {hours:.1f} hours")
        if hrv: lines.append(f"HRV_LAST_NIGHT: {hrv} ms")
        
        body_battery = readiness.get('bodyBatteryHigh')
        if body_battery: lines.append(f"BODY_BATTERY_START: {body_battery}")
        
        return "\n".join(lines) if lines else "READINESS DATA: Keys present but values empty."

    def _format_pace(self, speed_mps):
        """Convert m/s to min:sec/km."""
        if not speed_mps or speed_mps <= 0.1:
            return "-:--"
        pace_sec = 1000.0 / speed_mps
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        return f"{mins}:{secs:02d}"
