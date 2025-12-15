"""
Correlation Engine for AI Coach
Analyzes relationships between biometrics and performance
"""
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import statistics

import models


@dataclass
class CorrelationInsight:
    """A single correlation insight."""
    category: str  # "sleep", "hrv", "stress", "training_load"
    correlation: str  # "positive", "negative", "neutral"
    strength: float  # 0.0 to 1.0
    insight_text: str  # Turkish insight text
    data_points: int  # Number of data points used


@dataclass
class PerformanceCorrelations:
    """All correlation insights for a user."""
    sleep_performance: Optional[CorrelationInsight]
    hrv_recovery: Optional[CorrelationInsight]
    stress_performance: Optional[CorrelationInsight]
    training_load_status: Dict[str, Any]
    composite_insights: List[str]
    
    def to_context_string(self) -> str:
        """Convert to rich context for LLM."""
        parts = ["## PERFORMANS KORELASYONLARI"]
        
        if self.sleep_performance:
            parts.append(f"💤 Uyku: {self.sleep_performance.insight_text}")
        
        if self.hrv_recovery:
            parts.append(f"💓 HRV: {self.hrv_recovery.insight_text}")
        
        if self.stress_performance:
            parts.append(f"😰 Stres: {self.stress_performance.insight_text}")
        
        if self.training_load_status:
            tl = self.training_load_status
            parts.append(f"📊 Form: CTL={tl.get('ctl', 0):.1f}, ATL={tl.get('atl', 0):.1f}, TSB={tl.get('tsb', 0):.1f}")
            if tl.get('status'):
                parts.append(f"   Status: {tl['status']}")
        
        if self.composite_insights:
            parts.append("💡 Önemli: " + "; ".join(self.composite_insights[:3]))
        
        return "\n".join(parts)


class CorrelationEngine:
    """Analyzes correlations between biometrics and performance."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_correlations(self, user_id: int, days: int = 30) -> PerformanceCorrelations:
        """Get all correlation insights for a user."""
        return PerformanceCorrelations(
            sleep_performance=self.analyze_sleep_performance(user_id, days),
            hrv_recovery=self.analyze_hrv_recovery(user_id, days),
            stress_performance=self.analyze_stress_performance(user_id, days),
            training_load_status=self.get_training_load_status(user_id),
            composite_insights=self.generate_composite_insights(user_id, days)
        )
    
    def analyze_sleep_performance(self, user_id: int, days: int = 30) -> Optional[CorrelationInsight]:
        """
        Analyze correlation between sleep quality and next-day performance.
        Good sleep → Lower HR at same pace, better recovery
        """
        start_date = date.today() - timedelta(days=days)
        
        # Get sleep logs
        sleep_logs = self.db.query(models.SleepLog).filter(
            models.SleepLog.user_id == user_id,
            models.SleepLog.calendar_date >= start_date
        ).all()
        
        if len(sleep_logs) < 7:
            return CorrelationInsight(
                category="sleep",
                correlation="neutral",
                strength=0.0,
                insight_text="Yeterli uyku verisi yok (7 günden az)",
                data_points=len(sleep_logs)
            )
        
        # Get activities
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date
        ).all()
        
        if len(activities) < 5:
            return CorrelationInsight(
                category="sleep",
                correlation="neutral",
                strength=0.0,
                insight_text="Yeterli aktivite verisi yok",
                data_points=len(activities)
            )
        
        # Match sleep to next-day activities
        good_sleep_runs = []  # HR on runs after good sleep
        poor_sleep_runs = []  # HR on runs after poor sleep
        
        sleep_by_date = {s.calendar_date: s for s in sleep_logs}
        
        for activity in activities:
            if not activity.local_start_date or not activity.average_hr:
                continue
            
            prev_night = activity.local_start_date - timedelta(days=1)
            sleep = sleep_by_date.get(prev_night)
            
            if sleep and sleep.duration_seconds:
                hours = sleep.duration_seconds / 3600
                # Deep sleep ratio
                deep_ratio = (sleep.deep_seconds or 0) / sleep.duration_seconds if sleep.duration_seconds else 0
                
                if hours >= 7 and deep_ratio >= 0.15:  # Good sleep
                    good_sleep_runs.append(activity.average_hr)
                elif hours < 6 or deep_ratio < 0.10:  # Poor sleep
                    poor_sleep_runs.append(activity.average_hr)
        
        if len(good_sleep_runs) < 3 or len(poor_sleep_runs) < 3:
            return CorrelationInsight(
                category="sleep",
                correlation="neutral",
                strength=0.3,
                insight_text="Henüz net bir korelasyon tespit edilemedi",
                data_points=len(good_sleep_runs) + len(poor_sleep_runs)
            )
        
        avg_good = statistics.mean(good_sleep_runs)
        avg_poor = statistics.mean(poor_sleep_runs)
        hr_diff = avg_poor - avg_good
        
        if hr_diff > 5:
            return CorrelationInsight(
                category="sleep",
                correlation="positive",
                strength=min(hr_diff / 15, 1.0),
                insight_text=f"İyi uyku sonrası HR ortalama {hr_diff:.0f} bpm daha düşük. 7+ saat uyku önemli!",
                data_points=len(good_sleep_runs) + len(poor_sleep_runs)
            )
        elif hr_diff < -3:
            return CorrelationInsight(
                category="sleep",
                correlation="negative",
                strength=0.3,
                insight_text="Uyku-performans ilişkisi zayıf - diğer faktörler daha etkili",
                data_points=len(good_sleep_runs) + len(poor_sleep_runs)
            )
        else:
            return CorrelationInsight(
                category="sleep",
                correlation="neutral",
                strength=0.5,
                insight_text="Uyku kalitesi performansı orta düzeyde etkiliyor",
                data_points=len(good_sleep_runs) + len(poor_sleep_runs)
            )
    
    def analyze_hrv_recovery(self, user_id: int, days: int = 30) -> Optional[CorrelationInsight]:
        """
        Analyze HRV status vs recovery ability.
        Low HRV → Poor recovery, avoid hard workouts
        """
        start_date = date.today() - timedelta(days=days)
        
        # Get HRV logs
        hrv_logs = self.db.query(models.HRVLog).filter(
            models.HRVLog.user_id == user_id,
            models.HRVLog.calendar_date >= start_date
        ).all()
        
        if len(hrv_logs) < 7:
            return CorrelationInsight(
                category="hrv",
                correlation="neutral",
                strength=0.0,
                insight_text="Yeterli HRV verisi yok",
                data_points=len(hrv_logs)
            )
        
        # Get activities with recovery time
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date,
            models.Activity.recovery_time.isnot(None)
        ).all()
        
        if len(activities) < 5:
            return CorrelationInsight(
                category="hrv",
                correlation="neutral",
                strength=0.0,
                insight_text="Yeterli recovery verisi yok",
                data_points=len(activities)
            )
        
        # Match HRV to same-day activities
        hrv_by_date = {h.calendar_date: h for h in hrv_logs}
        
        low_hrv_recovery = []
        high_hrv_recovery = []
        
        for activity in activities:
            if not activity.local_start_date or not activity.recovery_time:
                continue
            
            hrv = hrv_by_date.get(activity.local_start_date)
            if hrv and hrv.last_night_avg and hrv.baseline_low:
                # Compare to baseline
                if hrv.last_night_avg < hrv.baseline_low:
                    low_hrv_recovery.append(activity.recovery_time)
                elif hrv.last_night_avg > hrv.baseline_high if hrv.baseline_high else hrv.baseline_low * 1.1:
                    high_hrv_recovery.append(activity.recovery_time)
        
        if len(low_hrv_recovery) < 2 or len(high_hrv_recovery) < 2:
            # Use status instead
            status_recovery = {"BALANCED": [], "UNBALANCED": [], "LOW": []}
            for activity in activities:
                hrv = hrv_by_date.get(activity.local_start_date)
                if hrv and hrv.status and activity.recovery_time:
                    if hrv.status in status_recovery:
                        status_recovery[hrv.status].append(activity.recovery_time)
            
            balanced_avg = statistics.mean(status_recovery["BALANCED"]) if len(status_recovery["BALANCED"]) >= 2 else 0
            low_avg = statistics.mean(status_recovery["LOW"]) if len(status_recovery["LOW"]) >= 2 else 0
            
            if balanced_avg > 0 and low_avg > 0:
                diff = low_avg - balanced_avg
                return CorrelationInsight(
                    category="hrv",
                    correlation="positive" if diff > 2 else "neutral",
                    strength=min(abs(diff) / 10, 1.0),
                    insight_text=f"HRV düşükken recovery {diff:.0f} saat daha uzun",
                    data_points=len(activities)
                )
        
        return CorrelationInsight(
            category="hrv",
            correlation="neutral",
            strength=0.4,
            insight_text="HRV-recovery ilişkisi izleniyor, henüz net patern yok",
            data_points=len(hrv_logs)
        )
    
    def analyze_stress_performance(self, user_id: int, days: int = 30) -> Optional[CorrelationInsight]:
        """
        Analyze stress levels vs workout performance.
        High stress → Higher HR at same pace, more cardiac drift
        """
        start_date = date.today() - timedelta(days=days)
        
        # Get stress logs
        stress_logs = self.db.query(models.StressLog).filter(
            models.StressLog.user_id == user_id,
            models.StressLog.calendar_date >= start_date
        ).all()
        
        if len(stress_logs) < 7:
            return CorrelationInsight(
                category="stress",
                correlation="neutral",
                strength=0.0,
                insight_text="Yeterli stres verisi yok",
                data_points=len(stress_logs)
            )
        
        # Calculate average stress
        avg_stress = statistics.mean([s.avg_stress for s in stress_logs if s.avg_stress])
        high_stress_days = sum(1 for s in stress_logs if s.avg_stress and s.avg_stress > 50)
        
        stress_ratio = high_stress_days / len(stress_logs)
        
        if stress_ratio > 0.5:
            return CorrelationInsight(
                category="stress",
                correlation="negative",
                strength=stress_ratio,
                insight_text=f"Günlerin %{stress_ratio*100:.0f}'inde yüksek stres! Bu koşularda sert antrenman kaçın",
                data_points=len(stress_logs)
            )
        elif stress_ratio > 0.3:
            return CorrelationInsight(
                category="stress",
                correlation="neutral",
                strength=0.5,
                insight_text=f"Ortalama stres seviyesi: {avg_stress:.0f}. Stresi yönetmeye devam",
                data_points=len(stress_logs)
            )
        else:
            return CorrelationInsight(
                category="stress",
                correlation="positive",
                strength=0.8,
                insight_text=f"Stres seviyesi kontrol altında ({avg_stress:.0f}). Sert antrenman için uygun!",
                data_points=len(stress_logs)
            )
    
    def get_training_load_status(self, user_id: int) -> Dict[str, Any]:
        """Get CTL, ATL, TSB from training load system."""
        # Try to use existing training_load.py if available
        try:
            from training_load import calculate_training_load
            result = calculate_training_load(self.db, user_id)
            if result:
                ctl = result.get('ctl', 0)
                atl = result.get('atl', 0)
                tsb = ctl - atl
                
                # Determine status
                if tsb < -20:
                    status = "Aşırı yorgun! ⚠️ Yükü azalt"
                elif tsb < -10:
                    status = "Yorgun - hafif antrenman önerilir"
                elif tsb < 5:
                    status = "Optimal form - performans için ideal"
                elif tsb < 15:
                    status = "Dinlenmiş - sert antrenman yapabilirsin"
                else:
                    status = "Çok dinlenmiş - fitness kaybı riski"
                
                return {
                    'ctl': ctl,
                    'atl': atl,
                    'tsb': tsb,
                    'status': status
                }
        except:
            pass
        
        # Fallback: calculate simple version
        return self._calculate_simple_training_load(user_id)
    
    def _calculate_simple_training_load(self, user_id: int) -> Dict[str, Any]:
        """Simple training load calculation fallback."""
        # Get last 42 days of activities
        start_date = date.today() - timedelta(days=42)
        
        activities = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.local_start_date >= start_date
        ).all()
        
        if len(activities) < 5:
            return {'ctl': 0, 'atl': 0, 'tsb': 0, 'status': 'Veri yetersiz'}
        
        # Simple: use duration * (avg_hr/max_hr) as load proxy
        daily_loads = {}
        for a in activities:
            if not a.local_start_date or not a.duration:
                continue
            
            hr_factor = (a.average_hr / a.max_hr) if a.average_hr and a.max_hr else 0.7
            load = (a.duration / 60) * hr_factor  # minutes * intensity
            
            daily_loads[a.local_start_date] = daily_loads.get(a.local_start_date, 0) + load
        
        # Calculate ATL (7-day) and CTL (42-day) averages
        today = date.today()
        atl_days = [(today - timedelta(days=i)) for i in range(7)]
        ctl_days = [(today - timedelta(days=i)) for i in range(42)]
        
        atl = sum(daily_loads.get(d, 0) for d in atl_days) / 7
        ctl = sum(daily_loads.get(d, 0) for d in ctl_days) / 42
        tsb = ctl - atl
        
        # Status
        if tsb < -15:
            status = "Yorgun - dinlenme günü önerilir"
        elif tsb < 5:
            status = "Optimal form"
        else:
            status = "Dinlenmiş - sert antrenman yapabilirsin"
        
        return {
            'ctl': ctl,
            'atl': atl,
            'tsb': tsb,
            'status': status
        }
    
    def generate_composite_insights(self, user_id: int, days: int = 30) -> List[str]:
        """Generate combined insights from all data sources."""
        insights = []
        
        # Get recent biometrics
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Yesterday's sleep
        sleep = self.db.query(models.SleepLog).filter(
            models.SleepLog.user_id == user_id,
            models.SleepLog.calendar_date == yesterday
        ).first()
        
        if sleep and sleep.duration_seconds:
            hours = sleep.duration_seconds / 3600
            if hours < 6:
                insights.append(f"Dün {hours:.1f} saat uyku - bugün hafif antrenman önerilir")
            elif hours >= 8:
                insights.append(f"İyi uyku ({hours:.1f}h) - bugün kaliteli iş yapabilirsin")
        
        # Today's HRV
        hrv = self.db.query(models.HRVLog).filter(
            models.HRVLog.user_id == user_id,
            models.HRVLog.calendar_date == today
        ).first()
        
        if hrv:
            if hrv.status == "LOW":
                insights.append("HRV düşük - vücut yüklü, sert antrenman kaçın")
            elif hrv.status == "BALANCED":
                insights.append("HRV dengeli - normal programa devam")
        
        # Today's stress
        stress = self.db.query(models.StressLog).filter(
            models.StressLog.user_id == user_id,
            models.StressLog.calendar_date == today
        ).first()
        
        if stress and stress.avg_stress:
            if stress.avg_stress > 60:
                insights.append(f"Stres yüksek ({stress.avg_stress}) - relaxing aktivite önerilir")
        
        return insights[:5]  # Max 5 insights
    
    def get_biometric_summary(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """Get summary of recent biometrics for LLM context."""
        start_date = date.today() - timedelta(days=days)
        
        # Sleep
        sleep_logs = self.db.query(models.SleepLog).filter(
            models.SleepLog.user_id == user_id,
            models.SleepLog.calendar_date >= start_date
        ).all()
        
        avg_sleep = None
        if sleep_logs:
            sleep_hours = [s.duration_seconds / 3600 for s in sleep_logs if s.duration_seconds]
            avg_sleep = statistics.mean(sleep_hours) if sleep_hours else None
        
        # HRV
        hrv_logs = self.db.query(models.HRVLog).filter(
            models.HRVLog.user_id == user_id,
            models.HRVLog.calendar_date >= start_date
        ).all()
        
        avg_hrv = None
        if hrv_logs:
            hrv_values = [h.last_night_avg for h in hrv_logs if h.last_night_avg]
            avg_hrv = statistics.mean(hrv_values) if hrv_values else None
        
        # Stress
        stress_logs = self.db.query(models.StressLog).filter(
            models.StressLog.user_id == user_id,
            models.StressLog.calendar_date >= start_date
        ).all()
        
        avg_stress = None
        if stress_logs:
            stress_values = [s.avg_stress for s in stress_logs if s.avg_stress]
            avg_stress = statistics.mean(stress_values) if stress_values else None
        
        return {
            'avg_sleep_hours': round(avg_sleep, 1) if avg_sleep else None,
            'avg_hrv': round(avg_hrv) if avg_hrv else None,
            'avg_stress': round(avg_stress) if avg_stress else None,
            'days_analyzed': days
        }
