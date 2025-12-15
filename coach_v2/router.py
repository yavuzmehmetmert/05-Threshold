"""
Coach V2 API Router
===================

FastAPI router for Coach V2 endpoints.
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from coach_v2.repository import CoachV2Repository
from coach_v2.orchestrator import CoachOrchestrator, ChatRequest
from coach_v2.pipeline import DailyPipeline
from coach_v2.llm_client import GeminiClient
from coach.crypto import decrypt_api_key
import models


router = APIRouter(prefix="/api/coach", tags=["coach_v2"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequestBody(BaseModel):
    user_id: int
    message: str
    garmin_activity_id: Optional[int] = None
    deep_analysis_mode: bool = False
    debug: bool = False
    conversation_history: list[ChatMessage] = []  # Last N messages for context


class ChatResponseBody(BaseModel):
    message: str
    resolved_activity_id: Optional[int] = None  # Activity being discussed
    debug_metadata: Optional[dict] = None


class NoteRequestBody(BaseModel):
    user_id: int
    note_text: str
    garmin_activity_id: Optional[int] = None
    note_type: str = "general"


class NoteResponseBody(BaseModel):
    id: int
    created_at: str


class BriefingResponseBody(BaseModel):
    briefing_text: str
    briefing_date: str
    generated_at: Optional[str] = None


class PipelineRequestBody(BaseModel):
    user_id: int
    force_full: bool = False


class PipelineResponseBody(BaseModel):
    status: str
    activities_processed: int = 0
    insights_generated: int = 0
    error: Optional[str] = None


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_llm_client(user_id: int, db: Session):
    """Get LLM client for a user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.gemini_api_key_encrypted:
        raise HTTPException(status_code=400, detail="User has no API key configured")
    
    api_key = decrypt_api_key(user.gemini_api_key_encrypted, user.gemini_api_key_iv or b'')
    return GeminiClient(api_key)


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/chat", response_model=ChatResponseBody)
async def chat(body: ChatRequestBody, db: Session = Depends(get_db)):
    """
    Chat with the AI coach.
    
    If garmin_activity_id is provided, the conversation will focus on that activity.
    If deep_analysis_mode is True, the system may query activity streams (slower).
    """
    llm_client = get_llm_client(body.user_id, db)
    orchestrator = CoachOrchestrator(db, llm_client)
    
    # Convert history to list of dicts
    history = [(msg.role, msg.content) for msg in body.conversation_history[-3:]]  # Last 3
    
    request = ChatRequest(
        user_id=body.user_id,
        message=body.message,
        garmin_activity_id=body.garmin_activity_id,
        deep_analysis_mode=body.deep_analysis_mode,
        debug=body.debug,
        conversation_history=history
    )
    
    response = orchestrator.handle_chat(request)
    
    return ChatResponseBody(
        message=response.message,
        resolved_activity_id=response.resolved_activity_id,
        debug_metadata=response.debug_metadata
    )


@router.get("/briefing", response_model=BriefingResponseBody)
async def get_briefing(
    user_id: int,
    date_str: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get daily briefing for a user.
    
    If date not provided, returns today's briefing.
    If no briefing exists, generates one on-demand.
    """
    repo = CoachV2Repository(db)
    
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    
    briefing = repo.get_briefing(user_id, target_date)
    
    if briefing:
        return BriefingResponseBody(
            briefing_text=briefing.briefing_text,
            briefing_date=str(briefing.briefing_date),
            generated_at=str(briefing.created_at)
        )
    
    # Generate on-demand
    pipeline = DailyPipeline(db)
    pipeline._generate_briefing(user_id, target_date)
    
    briefing = repo.get_briefing(user_id, target_date)
    if briefing:
        return BriefingResponseBody(
            briefing_text=briefing.briefing_text,
            briefing_date=str(briefing.briefing_date),
            generated_at=str(briefing.created_at)
        )
    
    # Fallback if still no briefing
    return BriefingResponseBody(
        briefing_text="Henüz yeterli veri yok. Biraz daha antrenman yap!",
        briefing_date=str(target_date)
    )


@router.post("/note", response_model=NoteResponseBody)
async def create_note(body: NoteRequestBody, db: Session = Depends(get_db)):
    """
    Create a user note.
    
    Notes can be general or attached to a specific activity.
    """
    repo = CoachV2Repository(db)
    
    note = repo.create_note(
        user_id=body.user_id,
        note_text=body.note_text,
        garmin_activity_id=body.garmin_activity_id,
        note_type=body.note_type
    )
    
    return NoteResponseBody(
        id=note.id,
        created_at=str(note.created_at)
    )


@router.post("/pipeline/run", response_model=PipelineResponseBody)
async def run_pipeline(body: PipelineRequestBody, db: Session = Depends(get_db)):
    """
    Manually trigger the daily pipeline for a user.
    
    This processes new activities, updates user model, and generates insights.
    Typically run nightly, but can be triggered manually.
    """
    pipeline = DailyPipeline(db)
    result = pipeline.run(body.user_id, force_full=body.force_full)
    
    return PipelineResponseBody(
        status=result.get('status', 'unknown'),
        activities_processed=result.get('activities_processed', 0),
        insights_generated=result.get('insights_generated', 0),
        error=result.get('error')
    )


@router.get("/summary/{garmin_activity_id}")
async def get_activity_summary(
    garmin_activity_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get the summary for a specific activity."""
    repo = CoachV2Repository(db)
    summary = repo.get_activity_summary(user_id, garmin_activity_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return {
        'garmin_activity_id': summary.garmin_activity_id,
        'facts_text': summary.facts_text,
        'summary_text': summary.summary_text,
        'workout_type': summary.workout_type,
        'local_start_date': str(summary.local_start_date)
    }


@router.get("/model/{user_id}")
async def get_user_model(user_id: int, db: Session = Depends(get_db)):
    """Get the learned user model."""
    repo = CoachV2Repository(db)
    model = repo.get_user_model_json(user_id)
    
    if not model:
        raise HTTPException(status_code=404, detail="User model not found. Run pipeline first.")
    
    return model
