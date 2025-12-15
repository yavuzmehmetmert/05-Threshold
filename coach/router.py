"""
FastAPI Router for AI Coach
Endpoints for chat, briefing, notes, and API key management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from database import get_db
import models
from coach.schemas import (
    ChatRequest, ChatResponse,
    BriefingRequest, BriefingResponse,
    NoteRequest, NoteResponse,
    APIKeyRequest, APIKeyResponse,
    LearnRequest, LearnResponse
)
from coach.orchestrator import Orchestrator
from coach.repository import CoachRepository
from coach.crypto import encrypt_api_key, decrypt_api_key, validate_api_key_format, mask_api_key


router = APIRouter(prefix="/coach", tags=["coach"])


def get_current_user_id(db: Session) -> int:
    """
    Get current user ID.
    For now, returns first user. In production, use auth.
    """
    user = db.query(models.User).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found")
    return user.id


# ============ Chat Endpoint ============

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat with AI coach.
    Uses progressive disclosure to minimize token usage.
    """
    user_id = get_current_user_id(db)
    orchestrator = Orchestrator(db, user_id)
    
    try:
        response = await orchestrator.handle_chat(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Briefing Endpoint ============

@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing(
    briefing_date: Optional[date] = None,
    force_regenerate: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get daily briefing for a date.
    Cached - regenerates only if force_regenerate=True.
    """
    user_id = get_current_user_id(db)
    orchestrator = Orchestrator(db, user_id)
    
    if briefing_date is None:
        briefing_date = date.today()
    
    # If force regenerate, clear cache first
    if force_regenerate:
        repo = CoachRepository(db)
        existing = repo.get_briefing(user_id, briefing_date)
        if existing:
            db.delete(existing)
            db.commit()
    
    try:
        response = await orchestrator.handle_briefing(briefing_date)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Note Endpoint ============

@router.post("/note", response_model=NoteResponse)
async def add_note(
    request: NoteRequest,
    db: Session = Depends(get_db)
):
    """
    Add a note for the coach (injury, goal, feedback).
    """
    user_id = get_current_user_id(db)
    repo = CoachRepository(db)
    
    try:
        note_id = repo.add_note(
            user_id=user_id,
            content=request.content,
            note_type=request.note_type,
            activity_id=request.activity_id
        )
        
        return NoteResponse(
            success=True,
            note_id=note_id,
            message="Not kaydedildi"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Learn Endpoint ============

@router.post("/learn", response_model=LearnResponse)
async def learn_user_history(
    request: LearnRequest = LearnRequest(),
    db: Session = Depends(get_db)
):
    """
    Trigger initial user history analysis.
    Extracts stable facts from training history.
    """
    user_id = get_current_user_id(db)
    orchestrator = Orchestrator(db, user_id)
    
    try:
        response = await orchestrator.handle_learn(force=request.force)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ API Key Management ============

@router.post("/api-key", response_model=APIKeyResponse)
async def set_api_key(
    request: APIKeyRequest,
    db: Session = Depends(get_db)
):
    """
    Set Gemini API key for user.
    Key is encrypted before storage.
    """
    user_id = get_current_user_id(db)
    
    # Validate format
    if not validate_api_key_format(request.api_key):
        return APIKeyResponse(
            success=False,
            message="Geçersiz API anahtarı formatı"
        )
    
    try:
        # Encrypt key
        encrypted, iv = encrypt_api_key(request.api_key)
        
        # Save to user
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.gemini_api_key_encrypted = encrypted
        user.gemini_api_key_iv = iv
        db.commit()
        
        return APIKeyResponse(
            success=True,
            masked_key=mask_api_key(request.api_key),
            message="API anahtarı kaydedildi"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-key", response_model=APIKeyResponse)
async def get_api_key_status(
    db: Session = Depends(get_db)
):
    """
    Check if API key is set (returns masked version).
    """
    user_id = get_current_user_id(db)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.gemini_api_key_encrypted:
        return APIKeyResponse(
            success=False,
            message="API anahtarı ayarlanmamış"
        )
    
    # Decrypt to get masked version
    api_key = decrypt_api_key(
        user.gemini_api_key_encrypted,
        user.gemini_api_key_iv or b""
    )
    
    if api_key:
        return APIKeyResponse(
            success=True,
            masked_key=mask_api_key(api_key),
            message="API anahtarı mevcut"
        )
    else:
        return APIKeyResponse(
            success=False,
            message="API anahtarı çözülemedi"
        )


@router.delete("/api-key", response_model=APIKeyResponse)
async def delete_api_key(
    db: Session = Depends(get_db)
):
    """
    Remove API key.
    """
    user_id = get_current_user_id(db)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.gemini_api_key_encrypted = None
    user.gemini_api_key_iv = None
    db.commit()
    
    return APIKeyResponse(
        success=True,
        message="API anahtarı silindi"
    )


@router.post("/api-key/test", response_model=APIKeyResponse)
async def test_api_key(
    db: Session = Depends(get_db)
):
    """
    Test the stored API key by making a simple call to Gemini.
    """
    user_id = get_current_user_id(db)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.gemini_api_key_encrypted:
        return APIKeyResponse(
            success=False,
            message="API anahtarı ayarlanmamış"
        )
    
    # Decrypt key
    api_key = decrypt_api_key(
        user.gemini_api_key_encrypted,
        user.gemini_api_key_iv or b""
    )
    
    if not api_key:
        return APIKeyResponse(
            success=False,
            message="API anahtarı çözülemedi"
        )
    
    # Test with Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'API key works!' in 3 words.")
        
        if response and response.text:
            return APIKeyResponse(
                success=True,
                masked_key=mask_api_key(api_key),
                message="Gemini API bağlantısı başarılı! ✓"
            )
        else:
            return APIKeyResponse(
                success=False,
                message="API yanıt vermedi"
            )
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return APIKeyResponse(
                success=False,
                message="API anahtarı geçersiz"
            )
        elif "quota" in error_msg.lower():
            return APIKeyResponse(
                success=False,
                message="API kota sınırı aşıldı"
            )
        else:
            return APIKeyResponse(
                success=False,
                message=f"Bağlantı hatası: {error_msg[:50]}"
            )


# ============ Conversation Management ============

@router.delete("/conversation")
async def clear_conversation(
    db: Session = Depends(get_db)
):
    """
    Clear conversation history and start fresh.
    """
    user_id = get_current_user_id(db)
    repo = CoachRepository(db)
    
    repo.clear_conversation_state(user_id)
    
    return {"success": True, "message": "Konuşma geçmişi temizlendi"}
