"""
Coach V2 Training Load Engine
=============================

Calculates daily fitness (CTL), fatigue (ATL), and form (TSB) metrics.
Based on Bannister's impulse-response model ideas (Coggan's TSS/CTL/ATL).

Formulas:
- TSS = (sec * NP * IF) / (FTP * 3600) * 100
- ATL (Acute Training Load) = exp. weighted avg of TSS (7 days)
- CTL (Chronic Training Load) = exp. weighted avg of TSS (42 days)
- TSB (Training Stress Balance) = CTL - ATL

Since we might lack power data, we use hrTSS or rTSS (Run TSS) approximations.
"""

from typing import List, Dict, Optional
from datetime import date, timedelta, datetime
import math
from sqlalchemy.orm import Session
from sqlalchemy import text

# Default Constants (if user profile missing)
DEFAULT_THRESHOLD_PACE = 300  # 5:00/km in seconds
DEFAULT_THRESHOLD_HR = 170

class TrainingLoadEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_current_load(self, user_id: int, target_date: date = None) -> Dict:
        """
        Get the CURRENT training load metrics using the same calculation as homepage.
        Uses training_load.calculate_pmc for consistency with dashboard.
        """
        if target_date is None:
            target_date = date.today()
        
        # Import the training_load module used by homepage
        try:
            import training_load as tl
            import models
            
            # Get all activities for this user (same query as ingestion_service)
            activities = self.db.query(models.Activity).filter(
                models.Activity.user_id == user_id
            ).order_by(models.Activity.start_time_local.asc()).all()
            
            # Convert to dict list (same format as ingestion_service)
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
            
            # Calculate PMC using the same function as dashboard
            # Pass target_date to get load at that specific date
            pmc = tl.calculate_pmc(act_list, days=365, end_date=target_date)
            
            return {
                'tss': pmc.get('weekly_tss', 0),
                'atl': pmc['atl'],
                'ctl': pmc['ctl'],
                'tsb': pmc['tsb'],
                'form_status': pmc.get('form_status', 'UNKNOWN')
            }
            
        except Exception as e:
            logging.warning(f"Failed to calculate PMC: {e}")
            # Fallback to stored data
            stored = self._get_load_record(user_id, target_date)
            if stored:
                return {
                    'tss': stored.get('tss', 0),
                    'atl': stored['atl_7'],
                    'ctl': stored['ctl_42'],
                    'tsb': stored['ctl_42'] - stored['atl_7']
                }
            return {'tss': 0, 'atl': 0, 'ctl': 0, 'tsb': 0}

    def calculate_sync_load(self, user_id: int, target_date: date):
        """
        Calculate and persist training load for a specific date.
        Updates ATL/CTL/TSB based on history.
        """
        # 1. Calculate Daily TSS
        tss = self._calculate_daily_tss(user_id, target_date)
        
        # 2. Get previous day's load
        prev_date = target_date - timedelta(days=1)
        prev_load = self._get_load_record(user_id, prev_date)
        
        prev_atl = prev_load['atl_7'] if prev_load else 0.0
        prev_ctl = prev_load['ctl_42'] if prev_load else 0.0
        
        # 3. Apply Exponential Weighted Moving Average (EWMA)
        atl = prev_atl + (tss - prev_atl) / 7.0
        ctl = prev_ctl + (tss - prev_ctl) / 42.0
        tsb = ctl - atl
        
        # 4. Persist
        self._upsert_daily_load(user_id, target_date, tss, atl, ctl, tsb)
        
        return {
            'tss': round(tss, 1),
            'atl': round(atl, 1),
            'ctl': round(ctl, 1),
            'tsb': round(tsb, 1)
        }

    def get_health_data(self, user_id: int, target_date: date) -> Dict:
        """
        Get health metrics (sleep, HRV, stress) for a date.
        """
        health = {}
        
        # Sleep
        sleep = self.db.execute(text("""
            SELECT sleep_score, duration_seconds, deep_seconds, rem_seconds, quality_score
            FROM sleep_logs 
            WHERE user_id = :uid AND calendar_date = :date
        """), {'uid': user_id, 'date': target_date}).fetchone()
        
        if sleep:
            duration_hrs = (sleep[1] or 0) / 3600
            deep_pct = int((sleep[2] or 0) / (sleep[1] or 1) * 100) if sleep[1] else 0
            rem_pct = int((sleep[3] or 0) / (sleep[1] or 1) * 100) if sleep[1] else 0
            health['sleep'] = {
                'score': sleep[0],
                'duration_hrs': round(duration_hrs, 1),
                'deep_pct': deep_pct,
                'rem_pct': rem_pct,
                'quality': sleep[4]
            }
        
        # HRV
        hrv = self.db.execute(text("""
            SELECT last_night_avg, status, baseline_low, baseline_high
            FROM hrv_logs 
            WHERE user_id = :uid AND calendar_date = :date
        """), {'uid': user_id, 'date': target_date}).fetchone()
        
        if hrv:
            health['hrv'] = {
                'value': hrv[0],
                'status': hrv[1],
                'baseline_low': hrv[2],
                'baseline_high': hrv[3]
            }
        
        # Stress
        stress = self.db.execute(text("""
            SELECT avg_stress, max_stress, status
            FROM stress_logs 
            WHERE user_id = :uid AND calendar_date = :date
        """), {'uid': user_id, 'date': target_date}).fetchone()
        
        if stress:
            health['stress'] = {
                'avg': stress[0],
                'max': stress[1],
                'status': stress[2]
            }
        
        return health


    def backfill_history(self, user_id: int, days: int = 90):
        """Recompute load for the last N days."""
        start_date = date.today() - timedelta(days=days)
        current = start_date
        today = date.today()
        
        while current <= today:
            self.calculate_sync_load(user_id, current)
            current += timedelta(days=1)

    def _calculate_daily_tss(self, user_id: int, target_date: date) -> float:
        """Sum specific activity TSS for the day from ALL activity sources."""
        total_tss = 0.0
        
        # First try coach_v2 summaries (pre-computed)
        try:
            summaries = self.db.execute(text("""
                SELECT summary_json, workout_type 
                FROM coach_v2.activity_summaries 
                WHERE user_id = :uid AND local_start_date = :date
            """), {'uid': user_id, 'date': target_date}).fetchall()
            
            for row in summaries:
                summary = row[0]
                if summary:
                    total_tss += self._estimate_tss(summary)
        except Exception:
            pass  # Table might not exist
        
        # ALWAYS also check public.activities for any missed activities
        try:
            activities = self.db.execute(text("""
                SELECT duration, average_hr, distance, avg_speed
                FROM activities 
                WHERE user_id = :uid AND local_start_date = :date
                AND activity_type LIKE '%running%'
            """), {'uid': user_id, 'date': target_date}).fetchall()
            
            for row in activities:
                duration_sec = row[0] or 0
                avg_hr = row[1]
                distance = row[2] or 0
                avg_speed = row[3]
                
                # Build summary dict for estimation
                summary = {
                    'duration_min': duration_sec / 60 if duration_sec else 0,
                    'avg_hr': avg_hr,
                    'distance_km': distance / 1000 if distance else 0
                }
                
                activity_tss = self._estimate_tss(summary)
                
                # Only add if we didn't already count it from summaries
                # (simple heuristic: if total_tss is 0, use this)
                if total_tss == 0:
                    total_tss += activity_tss
                    
        except Exception as e:
            logging.warning(f"Error fetching activities: {e}")
            pass
            
        return total_tss

    def _estimate_tss(self, summary: Dict) -> float:
        """
        Estimate TSS from summary data.
        Order of preference:
        1. hrTSS (if avg_hr and duration available)
        2. rTSS (if distance and duration available)
        3. Simple TRIMP-like proxy
        """
        if not summary:
            return 0.0
            
        duration_sec = (summary.get('duration_min', 0) or 0) * 60
        if duration_sec <= 0:
            return 0.0
            
        avg_hr = summary.get('avg_hr')
        distance_km = summary.get('distance_km', 0)
        
        # Method 1: HR-based (hrTSS)
        # Assuming LTHR = DEFAULT_THRESHOLD_HR for now (TODO: Fetch from User Profile)
        if avg_hr:
            lthr = DEFAULT_THRESHOLD_HR
            intensity = avg_hr / lthr
            # IF is roughly linear with HR ratio, but stress is quadratic
            # Simple formula: TSS = (sec * intensity^2) / 3600 * 100
            # This is a simplification of Bannister's TRIMP scaled to TSS
            if intensity > 1.1: intensity = 1.1 # Cap
            tss = (duration_sec * (intensity ** 2)) / 3600 * 100
            return tss

        # Method 2: Pace-based (rTSS)
        if distance_km > 0:
            speed_mps = (distance_km * 1000) / duration_sec
            threshold_mps = 1000.0 / DEFAULT_THRESHOLD_PACE
            intensity = speed_mps / threshold_mps
            # rTSS formula involves NGP, this is simplified
            tss = (duration_sec * (intensity ** 2)) / 3600 * 100
            return tss
            
        return 0.0

    def _get_load_record(self, user_id: int, target_date: date):
        """Get load record for a date."""
        row = self.db.execute(text("""
            SELECT atl_7, ctl_42 
            FROM coach_v2.daily_training_load 
            WHERE user_id = :uid AND calendar_date = :date
        """), {'uid': user_id, 'date': target_date}).fetchone()
        
        if row:
            return {'atl_7': row[0], 'ctl_42': row[1]}
        return None

    def _upsert_daily_load(self, user_id: int, target_date: date, tss, atl, ctl, tsb):
        """Save calculations."""
        self.db.execute(text("""
            INSERT INTO coach_v2.daily_training_load 
                (user_id, calendar_date, tss, atl_7, ctl_42, tsb, updated_at)
            VALUES 
                (:uid, :date, :tss, :atl, :ctl, :tsb, now())
            ON CONFLICT (user_id, calendar_date) DO UPDATE SET
                tss = :tss,
                atl_7 = :atl,
                ctl_42 = :ctl,
                tsb = :tsb,
                updated_at = now()
        """), {
            'uid': user_id,
            'date': target_date,
            'tss': tss,
            'atl': atl,
            'ctl': ctl,
            'tsb': tsb
        })
        self.db.commit()
