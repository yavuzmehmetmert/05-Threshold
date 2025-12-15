"""
Tool Functions for AI Coach
Bounded output tools that the LLM can call
Each tool has strict limits on returned data
"""
from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from sqlalchemy.orm import Session

from coach.repository import CoachRepository
from coach.schemas import ActivitySummary, RecentSummary, UserProfileSummary


# ============ Tool Decorator ============

def tool(name: str, description: str, parameters: Dict[str, Any]):
    """Decorator to mark functions as LLM tools with schema."""
    def decorator(func):
        func.__tool_schema__ = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        func.__tool_name__ = name
        return func
    return decorator


# ============ Tool Definitions ============

class CoachTools:
    """
    Collection of tools the AI coach can use.
    All methods return bounded, summarized data.
    """
    
    # Hard limits
    MAX_ACTIVITIES = 10
    MAX_DAYS = 30
    MAX_CHARS = 1000
    MAX_RAG_SNIPPETS = 3
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.repo = CoachRepository(db)
        self._call_log: List[Dict] = []  # Track tool calls
    
    def get_call_log(self) -> List[Dict]:
        """Get log of tool calls made."""
        return self._call_log
    
    def _log_call(self, name: str, chars: int):
        """Log a tool call."""
        self._call_log.append({"name": name, "chars": chars})
    
    @tool(
        name="get_user_profile",
        description="Kullanıcının temel profil bilgilerini al (isim, VO2max, RHR, yaş)",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    def get_user_profile(self) -> str:
        """
        Get compact user profile (~100 chars).
        Always call this first.
        """
        profile = self.repo.get_user_profile_summary(self.user_id)
        if not profile:
            result = "Kullanıcı bulunamadı"
        else:
            result = profile.to_context_string()
        
        self._log_call("get_user_profile", len(result))
        return result
    
    @tool(
        name="get_user_facts",
        description="Kullanıcı hakkında AI tarafından çıkarılan sabit gerçekleri al (hedefler, sakatlık geçmişi, tercihler)",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    def get_user_facts(self) -> str:
        """
        Get AI-extracted user facts (~500 chars).
        """
        facts = self.repo.get_user_facts(self.user_id)
        if not facts or not facts.facts_summary:
            result = "Henüz analiz yapılmamış. /learn çağrılmalı."
        else:
            parts = [facts.facts_summary]
            if facts.training_preferences:
                parts.append(f"Tercihler: {facts.training_preferences}")
            if facts.achievements:
                parts.append(f"Başarılar: {facts.achievements}")
            result = "\n".join(parts)
        
        # Truncate to limit
        if len(result) > self.MAX_CHARS:
            result = result[:self.MAX_CHARS] + "..."
        
        self._log_call("get_user_facts", len(result))
        return result
    
    @tool(
        name="get_recent_activities",
        description="Son aktivitelerin özetini al",
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Kaç günlük (maks 30)",
                    "default": 7
                },
                "limit": {
                    "type": "integer",
                    "description": "Maksimum aktivite sayısı (maks 10)",
                    "default": 5
                }
            },
            "required": []
        }
    )
    def get_recent_activities(self, days: int = 7, limit: int = 5) -> str:
        """
        Get compact summaries of recent activities.
        """
        # Enforce limits
        days = min(days, self.MAX_DAYS)
        limit = min(limit, self.MAX_ACTIVITIES)
        
        activities = self.repo.get_recent_activity_summaries(
            self.user_id, days=days, limit=limit
        )
        
        if not activities:
            result = f"Son {days} günde aktivite yok"
        else:
            lines = [a.to_context_string() for a in activities]
            result = "\n".join(lines)
        
        # Truncate to limit
        if len(result) > self.MAX_CHARS:
            result = result[:self.MAX_CHARS] + "..."
        
        self._log_call("get_recent_activities", len(result))
        return result
    
    @tool(
        name="get_recent_summary",
        description="Son dönemin toplam istatistiklerini al (toplam mesafe, süre, aktivite sayısı)",
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Kaç günlük (maks 30)",
                    "default": 7
                }
            },
            "required": []
        }
    )
    def get_recent_summary(self, days: int = 7) -> str:
        """
        Get aggregate summary of recent training.
        """
        days = min(days, self.MAX_DAYS)
        summary = self.repo.get_recent_summary(self.user_id, days=days)
        result = summary.to_context_string()
        
        self._log_call("get_recent_summary", len(result))
        return result
    
    @tool(
        name="get_activity_detail",
        description="Belirli bir aktivitenin detaylarını al",
        parameters={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "Aktivite ID"
                }
            },
            "required": ["activity_id"]
        }
    )
    def get_activity_detail(self, activity_id: int) -> str:
        """
        Get detailed summary of a specific activity.
        """
        activity = self.repo.get_activity_summary(self.user_id, activity_id)
        
        if not activity:
            result = f"Aktivite #{activity_id} bulunamadı"
        else:
            result = activity.to_context_string()
        
        self._log_call("get_activity_detail", len(result))
        return result
    
    @tool(
        name="get_last_activity",
        description="En son aktivitenin özetini al",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    def get_last_activity(self) -> str:
        """
        Get summary of most recent activity.
        """
        activity = self.repo.get_last_activity_summary(self.user_id)
        
        if not activity:
            result = "Henüz aktivite yok"
        else:
            result = activity.to_context_string()
        
        self._log_call("get_last_activity", len(result))
        return result
    
    @tool(
        name="get_training_load",
        description="Mevcut antrenman yükü metriklerini al (CTL, ATL, TSB)",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    def get_training_load(self) -> str:
        """
        Get current training load metrics.
        """
        load = self.repo.get_training_load_summary(self.user_id)
        
        if not load.get("ctl"):
            result = "Yeterli veri yok"
        else:
            result = (
                f"CTL (Fitness): {load['ctl']:.1f}, "
                f"ATL (Fatigue): {load['atl']:.1f}, "
                f"TSB (Form): {load['tsb']:.1f}"
            )
        
        self._log_call("get_training_load", len(result))
        return result
    
    @tool(
        name="get_biometrics",
        description="Son dönemin biyometrik özetini al (uyku, HRV, stres)",
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Kaç günlük (maks 7)",
                    "default": 7
                }
            },
            "required": []
        }
    )
    def get_biometrics(self, days: int = 7) -> str:
        """
        Get recent biometrics summary.
        """
        days = min(days, 7)
        bio = self.repo.get_recent_biometrics_summary(self.user_id, days=days)
        
        parts = []
        if bio.get("avg_sleep_hours"):
            parts.append(f"Ort. Uyku: {bio['avg_sleep_hours']:.1f}h")
        if bio.get("avg_hrv"):
            parts.append(f"Ort. HRV: {bio['avg_hrv']}")
        if bio.get("avg_stress"):
            parts.append(f"Ort. Stres: {bio['avg_stress']}")
        
        result = ", ".join(parts) if parts else "Biyometrik veri yok"
        
        self._log_call("get_biometrics", len(result))
        return result
    
    def get_all_tools(self) -> Dict[str, callable]:
        """Get dict of all tool functions."""
        return {
            "get_user_profile": self.get_user_profile,
            "get_user_facts": self.get_user_facts,
            "get_recent_activities": self.get_recent_activities,
            "get_recent_summary": self.get_recent_summary,
            "get_activity_detail": self.get_activity_detail,
            "get_last_activity": self.get_last_activity,
            "get_training_load": self.get_training_load,
            "get_biometrics": self.get_biometrics,
        }
    
    def get_tool_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM."""
        schemas = []
        for _, func in self.get_all_tools().items():
            if hasattr(func, '__tool_schema__'):
                schemas.append(func.__tool_schema__)
        return schemas
