"""
Pydantic Schemas for AI Coach
Request/Response models with token-efficient design
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class ChatMode(str, Enum):
    CHAT = "chat"
    BRIEFING = "briefing"
    ACTIVITY = "activity"
    LEARN = "learn"


class IntentType(str, Enum):
    GENERAL_CHAT = "general_chat"
    ACTIVITY_SPECIFIC = "activity_specific"
    SCIENCE_QUESTION = "science_question"
    TRAINING_ADVICE = "training_advice"
    INJURY_CONCERN = "injury_concern"
    GOAL_DISCUSSION = "goal_discussion"


# ============ Request Schemas ============

class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    message: str = Field(..., max_length=2000)
    activity_id: Optional[int] = None  # If asking about specific activity
    mode: ChatMode = ChatMode.CHAT
    debug_metadata: bool = False  # Include debug info in response


class BriefingRequest(BaseModel):
    """Request for daily briefing."""
    date: Optional[date] = None  # Default to today
    force_regenerate: bool = False


class NoteRequest(BaseModel):
    """Request to add a note to coach."""
    content: str = Field(..., max_length=1000)
    note_type: str = Field(default="general", pattern="^(general|injury|goal|feedback)$")
    activity_id: Optional[int] = None


class APIKeyRequest(BaseModel):
    """Request to set Gemini API key."""
    api_key: str = Field(..., min_length=30, max_length=100)


class LearnRequest(BaseModel):
    """Request to trigger initial user history analysis."""
    force: bool = False  # Re-analyze even if already done


# ============ Response Schemas ============

class DebugMetadata(BaseModel):
    """Debug information for development."""
    tools_called: List[str] = []
    chars_per_tool: Dict[str, int] = {}
    rag_snippets_count: int = 0
    rag_chars_total: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    intent_detected: Optional[str] = None
    cached_prefix_used: bool = True


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    message: str
    suggestions: List[str] = []  # Optional follow-up suggestions
    debug: Optional[DebugMetadata] = None


class BriefingResponse(BaseModel):
    """Response from briefing endpoint."""
    greeting: str
    training_status: str
    today_recommendation: str
    recovery_notes: Optional[str] = None
    motivation: Optional[str] = None
    full_text: str
    cached: bool = False
    debug: Optional[DebugMetadata] = None


class NoteResponse(BaseModel):
    """Response from note endpoint."""
    success: bool
    note_id: int
    message: str


class APIKeyResponse(BaseModel):
    """Response from API key endpoint."""
    success: bool
    masked_key: Optional[str] = None  # Show first/last 4 chars
    message: str


class LearnResponse(BaseModel):
    """Response from learn endpoint."""
    success: bool
    activities_analyzed: int
    facts_extracted: str
    message: str


# ============ Internal Schemas (Token-Efficient) ============

class UserProfileSummary(BaseModel):
    """Compact user profile for LLM context (~100 chars)."""
    name: str
    vo2max: Optional[int] = None
    resting_hr: Optional[int] = None
    age: Optional[int] = None
    
    def to_context_string(self) -> str:
        """Convert to minimal string for prompt."""
        parts = [f"Name: {self.name}"]
        if self.vo2max:
            parts.append(f"VO2max: {self.vo2max}")
        if self.resting_hr:
            parts.append(f"RHR: {self.resting_hr}")
        if self.age:
            parts.append(f"Age: {self.age}")
        return ", ".join(parts)


class ActivitySummary(BaseModel):
    """Compact activity summary for LLM context (~150 chars)."""
    id: int
    date: str
    type: str
    duration_min: int
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    notes: Optional[str] = None
    
    def to_context_string(self) -> str:
        """Convert to minimal string for prompt."""
        parts = [f"{self.date}: {self.type} {self.duration_min}min"]
        if self.distance_km:
            parts[0] += f" {self.distance_km:.1f}km"
        if self.avg_hr:
            parts.append(f"HR:{self.avg_hr}")
        if self.notes:
            parts.append(f"({self.notes[:50]})")
        return " ".join(parts)


class RecentSummary(BaseModel):
    """Compact summary of recent training (~200 chars)."""
    days: int
    total_activities: int
    total_distance_km: float
    total_duration_min: int
    avg_tss: Optional[float] = None
    trend: Optional[str] = None  # "increasing", "steady", "decreasing"
    
    def to_context_string(self) -> str:
        """Convert to minimal string for prompt."""
        return (
            f"Last {self.days}d: {self.total_activities} activities, "
            f"{self.total_distance_km:.1f}km, {self.total_duration_min}min total"
            + (f", trend: {self.trend}" if self.trend else "")
        )


class ConversationState(BaseModel):
    """Compressed conversation state (~800 chars max)."""
    rolling_summary: str = Field(default="", max_length=800)
    last_user_goal: str = Field(default="", max_length=300)
    last_turns: List[Dict[str, str]] = Field(default_factory=list)  # Max 3 turns
    turn_count: int = 0
    
    def to_context_string(self) -> str:
        """Convert to minimal string for prompt."""
        parts = []
        if self.rolling_summary:
            parts.append(f"Context: {self.rolling_summary}")
        if self.last_user_goal:
            parts.append(f"Goal: {self.last_user_goal}")
        turns = self.last_turns or []
        if turns:
            parts.append("Recent:")
            for turn in turns[-3:]:
                if turn:
                    role = turn.get("role", "user")
                    msg = turn.get("msg", "")[:100]
                    parts.append(f"  {role}: {msg}")
        return "\n".join(parts)


class RAGSnippet(BaseModel):
    """Retrieved knowledge snippet (~400 chars max)."""
    source: str
    topic: str
    content: str = Field(..., max_length=400)
    relevance_score: float = 0.0
    
    def to_context_string(self) -> str:
        """Convert to minimal string for prompt."""
        return f"[{self.topic}] {self.content}"
