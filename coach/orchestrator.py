"""
Orchestrator for AI Coach
Handles intent detection, progressive disclosure, and request routing
"""
import re
from typing import Optional, Dict, Any, Tuple
from datetime import date
from sqlalchemy.orm import Session
from enum import Enum

from coach.schemas import (
    ChatRequest, ChatResponse, BriefingResponse, LearnResponse,
    IntentType, DebugMetadata, ConversationState
)
from coach.repository import CoachRepository
from coach.tools import CoachTools
from coach.gemini_client import GeminiClient, GenerationResult
from coach.crypto import decrypt_api_key
import models


class Orchestrator:
    """
    Main orchestrator for AI coach requests.
    Implements progressive disclosure and token-efficient context building.
    """
    
    # Token budget thresholds
    TOKEN_BUDGET_TYPICAL = 2500
    TOKEN_BUDGET_MAX = 6000
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.repo = CoachRepository(db)
        self.tools = CoachTools(db, user_id)
        self._client: Optional[GeminiClient] = None
    
    def _get_client(self) -> Optional[GeminiClient]:
        """Get or create Gemini client for user."""
        if self._client:
            return self._client
        
        # Get user's API key
        user = self.db.query(models.User).filter(
            models.User.id == self.user_id
        ).first()
        
        if not user or not user.gemini_api_key_encrypted:
            return None
        
        api_key = decrypt_api_key(
            user.gemini_api_key_encrypted,
            user.gemini_api_key_iv or b""
        )
        
        if not api_key:
            return None
        
        self._client = GeminiClient(api_key=api_key)
        return self._client
    
    def detect_intent(self, message: str) -> IntentType:
        """
        Detect intent from user message.
        Used for progressive disclosure decisions.
        """
        message_lower = message.lower()
        
        # Injury/health concern patterns
        if any(word in message_lower for word in [
            "ağrı", "sakatlık", "yaralanma", "şişlik", "acı",
            "pain", "injury", "hurt", "sore"
        ]):
            return IntentType.INJURY_CONCERN
        
        # Activity-specific patterns
        if any(word in message_lower for word in [
            "son koşum", "dünkü", "bugünkü antrenman", "bu aktivite",
            "last run", "yesterday", "this activity"
        ]) or re.search(r"aktivite\s*#?\d+", message_lower):
            return IntentType.ACTIVITY_SPECIFIC
        
        # Science/knowledge patterns
        if any(word in message_lower for word in [
            "nedir", "nasıl çalışır", "bilimsel", "araştırma",
            "what is", "how does", "science", "research",
            "vo2max", "laktat", "threshold", "tempo", "interval"
        ]):
            return IntentType.SCIENCE_QUESTION
        
        # Training advice patterns
        if any(word in message_lower for word in [
            "antrenman", "program", "plan", "ne yapmalıyım", "öner",
            "training", "workout", "should i", "recommend"
        ]):
            return IntentType.TRAINING_ADVICE
        
        # Goal discussion patterns
        if any(word in message_lower for word in [
            "hedef", "maraton", "yarış", "pb", "pr", "kişisel rekor",
            "goal", "marathon", "race", "personal best"
        ]):
            return IntentType.GOAL_DISCUSSION
        
        return IntentType.GENERAL_CHAT
    
    def build_minimal_context(self) -> Dict[str, Any]:
        """
        Build minimal context for every request.
        ~400 tokens total.
        """
        context = {}
        
        # User profile (~100 chars)
        profile = self.repo.get_user_profile_summary(self.user_id)
        if profile:
            context["profile"] = profile.to_context_string()
        
        # Recent summary (~200 chars)
        recent = self.repo.get_recent_summary(self.user_id, days=7)
        context["recent_7d"] = recent.to_context_string()
        
        # Last activity (~150 chars)
        last_activity = self.repo.get_last_activity_summary(self.user_id)
        if last_activity:
            context["last_activity"] = last_activity.to_context_string()
        
        # Conversation state (~800 chars)
        conv_state = self.repo.get_conversation_state(self.user_id)
        if conv_state.turn_count > 0:
            context["conversation"] = conv_state.to_context_string()
        
        # User facts if available - FULL analysis from deep learning (~2000 chars)
        facts = self.repo.get_user_facts(self.user_id)
        if facts and facts.facts_summary:
            context["user_analysis"] = facts.facts_summary[:2000]
        
        return context
    
    def expand_context_for_intent(
        self, 
        intent: IntentType, 
        message: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Expand context based on detected intent.
        Progressive disclosure - only fetch what's needed.
        """
        # Activity-specific: extract ID and fetch details
        if intent == IntentType.ACTIVITY_SPECIFIC:
            activity_id = self._extract_activity_id(message)
            if activity_id:
                activity = self.repo.get_activity_summary(self.user_id, activity_id)
                if activity:
                    context["activity_detail"] = activity.to_context_string()
        
        # Training advice: add training load
        if intent in [IntentType.TRAINING_ADVICE, IntentType.GOAL_DISCUSSION]:
            load = self.repo.get_training_load_summary(self.user_id)
            if load.get("ctl"):
                context["training_load"] = (
                    f"CTL: {load['ctl']:.1f}, ATL: {load['atl']:.1f}, "
                    f"TSB: {load['tsb']:.1f}"
                )
        
        # Extended date range check
        if any(phrase in message.lower() for phrase in [
            "son ay", "4 hafta", "bir ay", "30 gün",
            "last month", "4 weeks", "30 days"
        ]):
            extended = self.repo.get_recent_summary(self.user_id, days=30)
            context["recent_30d"] = extended.to_context_string()
        
        return context
    
    def _extract_activity_id(self, message: str) -> Optional[int]:
        """Extract activity ID from message."""
        match = re.search(r"aktivite\s*#?(\d+)", message.lower())
        if match:
            return int(match.group(1))
        return None
    
    async def handle_chat(
        self, 
        request: ChatRequest
    ) -> ChatResponse:
        """
        Handle chat request with progressive disclosure.
        """
        client = self._get_client()
        if not client:
            return ChatResponse(
                message="⚠️ Gemini API anahtarı ayarlanmamış. Lütfen Profil > Ayarlar'dan API anahtarınızı girin.",
                suggestions=["API anahtarı nasıl alınır?"]
            )
        
        # 1. Detect intent
        intent = self.detect_intent(request.message)
        
        # 2. Build minimal context
        context = self.build_minimal_context()
        
        # 3. Expand context based on intent
        context = self.expand_context_for_intent(intent, request.message, context)
        
        # 4. Add activity context if provided
        if request.activity_id:
            activity = self.repo.get_activity_summary(self.user_id, request.activity_id)
            if activity:
                context["current_activity"] = activity.to_context_string()
        
        # 5. Check token budget
        estimated_tokens = client.estimate_request_tokens(
            request.message, 
            mode="chat", 
            context=context
        )
        
        if estimated_tokens > self.TOKEN_BUDGET_MAX:
            # Trim context to fit budget
            context = self._trim_context(context)
        
        # 6. Generate response with higher token limit for detailed answers
        result = client.generate(
            prompt=request.message,
            mode="chat",
            context=context,
            max_output_tokens=2048
        )
        
        # 7. Update conversation state
        self.repo.update_conversation_state(
            user_id=self.user_id,
            user_message=request.message,
            assistant_response=result.text
        )
        
        # 8. Build response
        response = ChatResponse(
            message=result.text,
            suggestions=self._generate_suggestions(intent, result.text)
        )
        
        # 9. Add debug metadata if requested
        if request.debug_metadata:
            response.debug = DebugMetadata(
                tools_called=[c["name"] for c in self.tools.get_call_log()],
                chars_per_tool={c["name"]: c["chars"] for c in self.tools.get_call_log()},
                estimated_input_tokens=result.usage.input_tokens,
                estimated_output_tokens=result.usage.output_tokens,
                intent_detected=intent.value,
                cached_prefix_used=True
            )
        
        return response
    
    def _trim_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Trim context to fit token budget."""
        # Priority order: profile, conversation, recent, facts
        priority = ["profile", "conversation", "recent_7d", "last_activity"]
        
        new_context = {}
        for key in priority:
            if key in context:
                new_context[key] = context[key]
        
        return new_context
    
    def _generate_suggestions(self, intent: IntentType, response: str) -> list:
        """Generate follow-up suggestions."""
        suggestions = []
        
        if intent == IntentType.TRAINING_ADVICE:
            suggestions = [
                "Bu antrenmanı ne zaman yapmalıyım?",
                "Alternatif bir antrenman var mı?"
            ]
        elif intent == IntentType.INJURY_CONCERN:
            suggestions = [
                "Ne kadar dinlenmeliyim?",
                "Hangi egzersizleri yapabilirim?"
            ]
        elif intent == IntentType.ACTIVITY_SPECIFIC:
            suggestions = [
                "Bu performansı nasıl geliştirebilirim?",
                "Sonraki antrenmanım ne olmalı?"
            ]
        
        return suggestions[:2]  # Max 2 suggestions
    
    async def handle_briefing(self, briefing_date: date = None) -> BriefingResponse:
        """
        Generate or retrieve daily briefing.
        """
        if briefing_date is None:
            briefing_date = date.today()
        
        # Check cache first
        cached = self.repo.get_briefing(self.user_id, briefing_date)
        if cached:
            return BriefingResponse(
                greeting=cached.greeting or "",
                training_status=cached.training_status or "",
                today_recommendation=cached.today_recommendation or "",
                recovery_notes=cached.recovery_notes,
                motivation=cached.motivation,
                full_text=cached.full_text or "",
                cached=True
            )
        
        # Generate new briefing
        client = self._get_client()
        if not client:
            return BriefingResponse(
                greeting="",
                training_status="",
                today_recommendation="",
                full_text="API anahtarı gerekli",
                cached=False
            )
        
        # Build context for briefing
        context = self.build_minimal_context()
        context["today"] = briefing_date.isoformat()
        
        # Add biometrics
        bio = self.repo.get_recent_biometrics_summary(self.user_id, days=3)
        if bio:
            context["biometrics"] = str(bio)
        
        # Generate
        result = client.generate(
            prompt=f"Günlük brifing oluştur: {briefing_date}",
            mode="briefing",
            context=context
        )
        
        # Parse structured response
        # For now, treat as full text
        briefing = BriefingResponse(
            greeting="",
            training_status="",
            today_recommendation="",
            full_text=result.text,
            cached=False
        )
        
        # Cache for later
        self.repo.save_briefing(
            user_id=self.user_id,
            briefing_date=briefing_date,
            greeting=briefing.greeting,
            training_status=briefing.training_status,
            today_recommendation=briefing.today_recommendation,
            full_text=briefing.full_text,
            tokens_used=result.usage.total
        )
        
        return briefing
    
    async def handle_learn(self, force: bool = False) -> LearnResponse:
        """
        Analyze user's full history and extract stable facts.
        This is the DEEP LEARNING phase - comprehensive user analysis.
        """
        # Check if already analyzed
        facts = self.repo.get_user_facts(self.user_id)
        if facts and facts.facts_summary and not force:
            return LearnResponse(
                success=True,
                activities_analyzed=facts.activities_analyzed_count or 0,
                facts_extracted=facts.facts_summary,
                message="Zaten analiz yapılmış. Tekrar analiz için force=True kullan."
            )
        
        client = self._get_client()
        if not client:
            return LearnResponse(
                success=False,
                activities_analyzed=0,
                facts_extracted="",
                message="API anahtarı gerekli"
            )
        
        # Get COMPREHENSIVE history for deep analysis
        activities = self.repo.get_recent_activity_summaries(
            self.user_id, days=365, limit=100  # Full year, 100 activities
        )
        
        # Get weekly summaries for trend analysis
        weekly_summaries = []
        for week_offset in range(0, 12):  # Last 12 weeks
            week_start = 7 * week_offset
            week_end = week_start + 7
            summary = self.repo.get_recent_summary(self.user_id, days=week_end)
            if summary:
                weekly_summaries.append(f"Week -{week_offset}: {summary.total_activities} runs, {summary.total_distance_km:.1f}km")
        
        # Build COMPREHENSIVE context
        context = {
            "profile": self.tools.get_user_profile(),
            "activity_history": "\n".join([a.to_context_string() for a in activities]),
            "weekly_trends": "\n".join(weekly_summaries),
            "biometrics_7d": self.tools.get_biometrics(days=7),
            "biometrics_30d": self.tools.get_biometrics(days=30),
            "training_load": self.tools.get_training_load(),
            "stats": {
                "total_activities": len(activities),
                "analysis_date": str(date.today()),
                "date_range": f"Last 365 days"
            }
        }
        
        # Use learn mode for DEEP analysis with high token output
        result = client.generate(
            prompt="""Kullanıcının TÜM antrenman geçmişini derinlemesine analiz et.

Bu bir "tanışma" sürecidir - her detayı incele:
- Antrenman paternleri ve tutarlılık
- Fizyolojik göstergeler ve trendler
- Gelişim eğrileri ve platolar
- Risk faktörleri ve uyarı işaretleri
- Başarılar ve kilometre taşları
- Benzersiz özellikler ve tercihler

Detaylı analiz raporu oluştur ve JSON özet ekle.""",
            mode="learn",
            context=context,
            max_output_tokens=4000,  # High token for comprehensive analysis
            temperature=0.3  # Lower temperature for accurate analysis
        )
        
        # Full analysis text
        full_analysis = result.text
        
        # Take first 2000 chars for facts_summary (main points)
        facts_summary = full_analysis[:2000] if len(full_analysis) > 2000 else full_analysis
        
        # Save to database with full analysis
        self.repo.save_user_facts(
            user_id=self.user_id,
            facts=facts_summary,
            preferences="",
            achievements=""
        )
        
        # Update activities analyzed count and save full analysis
        facts_record = self.repo.get_user_facts(self.user_id)
        if facts_record:
            facts_record.activities_analyzed_count = len(activities)
            # Save full analysis in a note for reference
            self.db.commit()
        
        # Also save full analysis as a coach note
        self.repo.add_note(
            user_id=self.user_id,
            content=full_analysis[:1000],
            note_type="general"
        )
        
        return LearnResponse(
            success=True,
            activities_analyzed=len(activities),
            facts_extracted=full_analysis,  # Return full analysis
            message="🎓 Derin analiz tamamlandı! Artık seni daha iyi tanıyorum."
        )
