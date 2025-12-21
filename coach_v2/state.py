"""
Conversation State Management
==============================

Manages user context including:
- Conversation history (last 5 turns)
- User physiological metrics (CTL, TSB, ATL)
- Activity context from pinned state
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import logging


@dataclass
class UserMetrics:
    """User's latest physiological metrics."""
    ctl: float = 0.0           # Chronic Training Load (42-day)
    atl: float = 0.0           # Acute Training Load (7-day)
    tsb: float = 0.0           # Training Stress Balance (CTL - ATL)
    resting_hr: int = 50       # Resting heart rate
    vo2max: int = 50           # VO2 max
    weight: float = 70.0       # Weight in kg
    sleep_score: int = 0       # Last night sleep score
    hrv: int = 0               # Last night HRV
    stress_avg: int = 0        # Yesterday's avg stress
    last_updated: Optional[datetime] = None


@dataclass 
class ConversationTurn:
    """Single conversation turn."""
    role: str           # 'user' or 'assistant'
    content: str        # Message content
    timestamp: datetime = field(default_factory=datetime.now)
    handler_type: Optional[str] = None  # Which handler processed this


class ConversationState:
    """
    Manages conversation state for a user session.
    
    - Stores last N turns of conversation history
    - Holds user's physiological metrics
    - Can be passed to handlers for context-aware responses
    """
    
    MAX_HISTORY = 5
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history: List[ConversationTurn] = []
        self.metrics = UserMetrics()
        self.created_at = datetime.now()
        self.last_activity_at = datetime.now()
    
    def add_turn(self, role: str, content: str, handler_type: Optional[str] = None):
        """
        Add a conversation turn.
        Automatically trims to MAX_HISTORY turns.
        """
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            handler_type=handler_type
        )
        self.history.append(turn)
        
        # Trim to max history
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]
        
        self.last_activity_at = datetime.now()
    
    def get_history_for_prompt(self) -> str:
        """
        Format conversation history for LLM prompt.
        Returns formatted string of recent turns.
        """
        if not self.history:
            return ""
        
        lines = ["KONUŞMA GEÇMİŞİ:"]
        for turn in self.history:
            role_label = "SPORCU" if turn.role == "user" else "HOCA"
            lines.append(f"[{role_label}]: {turn.content[:200]}{'...' if len(turn.content) > 200 else ''}")
        
        return "\n".join(lines)
    
    def get_history_as_list(self) -> List[Dict[str, str]]:
        """
        Return history as list of dicts for API response.
        """
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self.history
        ]
    
    def update_metrics_from_db(self, db: Session):
        """
        Fetch latest physiological metrics from database.
        """
        try:
            from models import PhysiologicalLog, SleepLog, HRVLog, StressLog, Activity
            from datetime import date, timedelta
            
            today = date.today()
            
            # Get latest physiological log
            phys_log = db.query(PhysiologicalLog).filter(
                PhysiologicalLog.user_id == self.user_id,
                PhysiologicalLog.vo2_max.isnot(None)
            ).order_by(PhysiologicalLog.calendar_date.desc()).first()
            
            if phys_log:
                self.metrics.resting_hr = phys_log.resting_hr or 50
                self.metrics.vo2max = phys_log.vo2_max or 50
                self.metrics.weight = phys_log.weight or 70.0
            
            # Get last night's sleep score
            sleep_log = db.query(SleepLog).filter(
                SleepLog.user_id == self.user_id
            ).order_by(SleepLog.calendar_date.desc()).first()
            
            if sleep_log:
                self.metrics.sleep_score = sleep_log.sleep_score or 0
            
            # Get last HRV
            hrv_log = db.query(HRVLog).filter(
                HRVLog.user_id == self.user_id
            ).order_by(HRVLog.calendar_date.desc()).first()
            
            if hrv_log:
                self.metrics.hrv = hrv_log.last_night_avg or 0
            
            # Get yesterday's stress
            stress_log = db.query(StressLog).filter(
                StressLog.user_id == self.user_id
            ).order_by(StressLog.calendar_date.desc()).first()
            
            if stress_log:
                self.metrics.stress_avg = stress_log.avg_stress or 0
            
            # Calculate CTL/ATL/TSB from recent activities
            self._calculate_training_load(db)
            
            self.metrics.last_updated = datetime.now()
            
        except Exception as e:
            logging.error(f"Error updating metrics: {e}")
    
    def _calculate_training_load(self, db: Session):
        """
        Calculate CTL (42-day), ATL (7-day), and TSB.
        Uses Training Effect as proxy for TSS if available.
        """
        try:
            from models import Activity
            from datetime import date, timedelta
            
            today = date.today()
            
            # Get activities from last 42 days
            activities = db.query(Activity).filter(
                Activity.user_id == self.user_id,
                Activity.local_start_date >= today - timedelta(days=42)
            ).all()
            
            if not activities:
                return
            
            # Calculate daily load using Training Effect * 20 as proxy for TSS
            daily_loads = {}
            for act in activities:
                act_date = act.local_start_date
                load = (act.training_effect or 2.0) * 20  # Proxy TSS
                daily_loads[act_date] = daily_loads.get(act_date, 0) + load
            
            # Calculate ATL (7-day exponential weighted average)
            atl_days = 7
            atl_sum = 0
            atl_count = 0
            for i in range(atl_days):
                d = today - timedelta(days=i)
                if d in daily_loads:
                    weight = 2 / (atl_days + 1) * ((atl_days - i) / atl_days)
                    atl_sum += daily_loads[d] * weight
                    atl_count += weight
            
            self.metrics.atl = round(atl_sum / max(atl_count, 1), 1)
            
            # Calculate CTL (42-day exponential weighted average)
            ctl_days = 42
            ctl_sum = 0
            ctl_count = 0
            for i in range(ctl_days):
                d = today - timedelta(days=i)
                if d in daily_loads:
                    weight = 2 / (ctl_days + 1) * ((ctl_days - i) / ctl_days)
                    ctl_sum += daily_loads[d] * weight
                    ctl_count += weight
            
            self.metrics.ctl = round(ctl_sum / max(ctl_count, 1), 1)
            
            # TSB = CTL - ATL
            self.metrics.tsb = round(self.metrics.ctl - self.metrics.atl, 1)
            
        except Exception as e:
            logging.error(f"Error calculating training load: {e}")
    
    def get_metrics_summary(self) -> str:
        """
        Return formatted metrics summary for LLM prompt.
        """
        return f"""SPORCU METRİKLERİ:
- Form (TSB): {self.metrics.tsb:+.0f} {'(Dinlenmiş)' if self.metrics.tsb > 0 else '(Yorgun)' if self.metrics.tsb < -10 else '(Normal)'}
- Fitness (CTL): {self.metrics.ctl:.0f}
- Yorgunluk (ATL): {self.metrics.atl:.0f}
- Dinlenme Nabzı: {self.metrics.resting_hr} bpm
- VO2max: {self.metrics.vo2max}
- Son Uyku Skoru: {self.metrics.sleep_score}/100
- Son HRV: {self.metrics.hrv} ms
- Son Stres: {self.metrics.stress_avg}/100"""


# ============================================================================
# STATE MANAGER (Global State Storage)
# ============================================================================

class StateManager:
    """
    Manages conversation states for multiple users.
    In-memory storage for now, could be Redis/DB later.
    """
    
    def __init__(self):
        self._states: Dict[int, ConversationState] = {}
    
    def get_or_create(self, user_id: int, db: Session = None) -> ConversationState:
        """
        Get existing state or create new one for user.
        Optionally refresh metrics from DB.
        """
        if user_id not in self._states:
            self._states[user_id] = ConversationState(user_id)
            if db:
                self._states[user_id].update_metrics_from_db(db)
        
        return self._states[user_id]
    
    def clear(self, user_id: int):
        """Clear state for a user."""
        if user_id in self._states:
            del self._states[user_id]
    
    def clear_all(self):
        """Clear all states."""
        self._states.clear()


# Global state manager instance
conversation_state_manager = StateManager()
