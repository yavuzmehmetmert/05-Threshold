"""
Coach V2 Orchestrator (Enhanced with Pinned State)
==================================================

Progressive disclosure chat handler with:
- Pinned activity/date state (persists across turns)
- Intent-based routing (health, laps, longitudinal, etc.)
- Context building based on intent (NO default last activity)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from coach_v2.repository import CoachV2Repository
from coach_v2.llm_client import LLMClient, LLMResponse
from coach_v2.query_understanding import parse_user_query, ParsedIntent, PinnedState
from coach_v2.candidate_retrieval import CandidateRetriever, Resolution, ActivityCandidate


# ==============================================================================
# CONTEXT BOUNDS
# ==============================================================================
MAX_CONTEXT_CHARS = 4000
MAX_RAG_CHARS = 1500


@dataclass
class ChatRequest:
    """Chat request from user."""
    user_id: int
    message: str
    garmin_activity_id: Optional[int] = None
    deep_analysis_mode: bool = False
    debug: bool = False
    conversation_history: List[tuple] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []


@dataclass 
class ChatResponse:
    """Chat response to user."""
    message: str
    resolved_activity_id: Optional[int] = None
    resolved_date: Optional[str] = None
    debug_metadata: Optional[Dict[str, Any]] = None


class ConversationStateManager:
    """Manages pinned activity/date state for multi-turn conversations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_pinned_state(self, user_id: int) -> PinnedState:
        """Get current pinned state for user (if not expired)."""
        result = self.db.execute(text("""
            SELECT pinned_garmin_activity_id, pinned_local_start_date, pinned_activity_name
            FROM coach_v2.conversation_state
            WHERE user_id = :user_id AND pinned_expires_at > now()
        """), {'user_id': user_id}).fetchone()
        
        if result:
            return PinnedState(
                garmin_activity_id=result[0],
                local_start_date=result[1],
                activity_name=result[2],
                is_valid=True
            )
        return PinnedState(is_valid=False)
    
    def pin_activity(
        self, 
        user_id: int, 
        activity_id: int, 
        local_date: date, 
        activity_name: str,
        intent_type: str
    ):
        """Pin an activity for future turns."""
        self.db.execute(text("""
            INSERT INTO coach_v2.conversation_state 
                (user_id, pinned_garmin_activity_id, pinned_local_start_date, 
                 pinned_activity_name, pinned_expires_at, last_intent, updated_at)
            VALUES 
                (:user_id, :activity_id, :local_date, :name, 
                 now() + INTERVAL '30 minutes', :intent, now())
            ON CONFLICT (user_id) DO UPDATE SET
                pinned_garmin_activity_id = :activity_id,
                pinned_local_start_date = :local_date,
                pinned_activity_name = :name,
                pinned_expires_at = now() + INTERVAL '30 minutes',
                last_intent = :intent,
                updated_at = now()
        """), {
            'user_id': user_id, 
            'activity_id': activity_id, 
            'local_date': local_date,
            'name': activity_name,
            'intent': intent_type
        })
        self.db.commit()
    
    def extend_expiry(self, user_id: int):
        """Extend pinned state expiry on activity."""
        self.db.execute(text("""
            UPDATE coach_v2.conversation_state 
            SET pinned_expires_at = now() + INTERVAL '30 minutes', updated_at = now()
            WHERE user_id = :user_id
        """), {'user_id': user_id})
        self.db.commit()


class CoachOrchestrator:
    """
    Progressive disclosure orchestrator with pinned state.
    
    Key principle: NO hardcoded last activity. Context is built based on intent.
    Pinned state persists across turns for follow-up questions.
    """
    
    SYSTEM_PROMPT = """Sen "Hoca" - sert ama babacan bir Türk koşu koçusun.

TEMEL KURALLAR:
1. Selamlaşmaya kısa ve samimi cevap ver.
2. Aktivite hakkında soru varsa → SADECE sana verilen BEGIN_FACTS bloğundaki veriyi kullan.
3. INTERVAL_STRUCTURE varsa VE kullanıcı antrenman sorusu soruyorsa → İlk cümlede interval yapısını belirt.
4. Sana veri verilmediyse → "Bu veri mevcut değil" de, UYDURMA.
5. Sağlık verisi (uyku/HRV/stres) sorulduysa → HEALTH_DATA bloğundaki verileri kullan.

TARZ:
- Kısa ve öz (max 150 kelime)
- Babacan ama profesyonel
- "Koşu yalan söylemez" gibi deyimler kullan"""

    def __init__(self, db: Session, llm_client: LLMClient):
        self.db = db
        self.repo = CoachV2Repository(db)
        self.llm = llm_client
        self.retriever = CandidateRetriever(db)
        self.state_manager = ConversationStateManager(db)
    
    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Handle chat request with pinned state awareness."""
        debug_info = {} if request.debug else None
        
        # 1. Get pinned state
        pinned_state = self.state_manager.get_pinned_state(request.user_id)
        
        if debug_info is not None:
            debug_info['pinned_activity_id'] = pinned_state.garmin_activity_id
            debug_info['pinned_date'] = str(pinned_state.local_start_date) if pinned_state.local_start_date else None
        
        # 2. Parse query with pinned state awareness
        parsed_intent = parse_user_query(request.message, pinned_state)
        
        if debug_info is not None:
            debug_info['intent_type'] = parsed_intent.intent_type
            debug_info['mentioned_dates'] = [str(d) for d in parsed_intent.mentioned_dates]
        
        # 3. Route based on intent
        
        # Greeting
        if parsed_intent.intent_type == 'greeting':
            return self._handle_greeting(request, debug_info)
        
        # Explicit activity ID provided
        if request.garmin_activity_id:
            return self._handle_specific_activity(request, request.garmin_activity_id, debug_info)
        
        # Date-specific query
        if parsed_intent.intent_type == 'specific_date':
            return self._handle_date_query(request, parsed_intent, debug_info)
        
        # Name-specific query
        if parsed_intent.intent_type == 'specific_name':
            return self._handle_name_query(request, parsed_intent, debug_info)
        
        # Health query (uses pinned date)
        if parsed_intent.intent_type == 'health_day_status':
            return self._handle_health_query(request, parsed_intent, pinned_state, debug_info)
        
        # Laps/splits query (uses pinned activity)
        if parsed_intent.intent_type == 'laps_or_splits':
            return self._handle_laps_query(request, parsed_intent, pinned_state, debug_info)
        
        # Longitudinal prep query (uses pinned date as anchor)
        if parsed_intent.intent_type == 'longitudinal_prep':
            return self._handle_longitudinal_query(request, parsed_intent, pinned_state, debug_info)
        
        # Activity analysis follow-up (uses pinned activity)
        if parsed_intent.intent_type == 'activity_analysis':
            return self._handle_activity_analysis(request, pinned_state, debug_info)
        
        # Trend query
        if parsed_intent.intent_type == 'trend':
            return self._handle_trend_query(request, parsed_intent, debug_info)
        
        # Last activity intent
        if parsed_intent.intent_type == 'last_activity':
            return self._handle_last_activity(request, debug_info)
        
        # General query
        return self._handle_general_query(request, debug_info)
    
    # ==========================================================================
    # INTENT HANDLERS
    # ==========================================================================
    
    def _handle_greeting(self, request: ChatRequest, debug_info: Optional[Dict]) -> ChatResponse:
        """Handle greeting - minimal context."""
        prompt = f"""{self.SYSTEM_PROMPT}

# KULLANICI MESAJI
{request.message}"""
        response = self.llm.generate(prompt, max_tokens=100)
        return ChatResponse(message=response.text, debug_metadata=debug_info)
    
    def _handle_date_query(
        self, 
        request: ChatRequest, 
        intent: ParsedIntent,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle date-specific query and PIN the resolved activity."""
        if not intent.mentioned_dates:
            return self._handle_general_query(request, debug_info)
        
        target_date = intent.mentioned_dates[0]
        candidates = self.retriever.get_candidates_by_date(request.user_id, target_date)
        
        if debug_info is not None:
            debug_info['target_date'] = str(target_date)
            debug_info['candidates_found'] = len(candidates)
        
        name_hint = intent.activity_name_keywords[0] if intent.activity_name_keywords else None
        resolution = self.retriever.resolve_candidates(candidates, name_hint)
        
        if resolution.status == 'selected':
            # PIN the activity for future turns
            activity = resolution.selected
            self.state_manager.pin_activity(
                request.user_id,
                activity.garmin_activity_id,
                activity.local_start_date,
                activity.activity_name,
                'specific_date'
            )
            return self._generate_with_activity(request, activity, debug_info)
        
        return self._handle_resolution(request, resolution, debug_info)
    
    def _handle_name_query(
        self, 
        request: ChatRequest, 
        intent: ParsedIntent,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle name-specific query."""
        if not intent.activity_name_keywords:
            return self._handle_general_query(request, debug_info)
        
        name_query = intent.activity_name_keywords[0]
        candidates = self.retriever.get_candidates_by_name(request.user_id, name_query)
        resolution = self.retriever.resolve_candidates(candidates, name_query)
        
        if resolution.status == 'selected':
            activity = resolution.selected
            self.state_manager.pin_activity(
                request.user_id,
                activity.garmin_activity_id,
                activity.local_start_date,
                activity.activity_name,
                'specific_name'
            )
            return self._generate_with_activity(request, activity, debug_info)
        
        return self._handle_resolution(request, resolution, debug_info)
    
    def _handle_activity_analysis(
        self, 
        request: ChatRequest, 
        pinned_state: PinnedState,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle follow-up analysis using pinned activity."""
        if not pinned_state.is_valid or not pinned_state.garmin_activity_id:
            return ChatResponse(
                message="Hangi aktiviteyi sorduğunu anlamadım. Lütfen tarih veya aktivite ismini belirt.",
                debug_metadata=debug_info
            )
        
        # Extend expiry
        self.state_manager.extend_expiry(request.user_id)
        
        # Get activity
        summary = self.repo.get_activity_summary(request.user_id, pinned_state.garmin_activity_id)
        if not summary:
            return ChatResponse(
                message="Bu aktivite için detaylı veri bulamadım.",
                debug_metadata=debug_info
            )
        
        activity = ActivityCandidate(
            garmin_activity_id=summary.garmin_activity_id,
            activity_name=pinned_state.activity_name or "",
            local_start_date=summary.local_start_date,
            distance_km=summary.summary_json.get('distance_km', 0) if summary.summary_json else 0,
            duration_min=summary.summary_json.get('duration_min', 0) if summary.summary_json else 0,
            workout_type=summary.workout_type,
            facts_text=summary.facts_text,
            summary_text=summary.summary_text
        )
        
        if debug_info is not None:
            debug_info['context_source'] = 'pinned_state'
        
        return self._generate_with_activity(request, activity, debug_info)
    
    def _handle_health_query(
        self, 
        request: ChatRequest, 
        intent: ParsedIntent,
        pinned_state: PinnedState,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle health/biometrics query for a specific date."""
        target_date = intent.anchor_date or (pinned_state.local_start_date if pinned_state.is_valid else None)
        
        if not target_date:
            return ChatResponse(
                message="Hangi gün için sağlık verisi istediğini anlamadım. Lütfen tarih belirt (örn: 9 mart 2025).",
                debug_metadata=debug_info
            )
        
        # Get health data for that date
        health_data = self._get_health_for_date(request.user_id, target_date)
        
        if not health_data:
            return ChatResponse(
                message=f"{target_date.strftime('%d %B %Y')} için sağlık verisi bulamadım.",
                debug_metadata=debug_info
            )
        
        # Build context
        context = f"""# SAĞLIK VERİLERİ ({target_date})
SLEEP_SCORE={health_data.get('sleep_score', 'N/A')}
HRV={health_data.get('hrv', 'N/A')}
STRESS_LEVEL={health_data.get('stress_level', 'N/A')}
RESTING_HR={health_data.get('resting_hr', 'N/A')}
BODY_BATTERY={health_data.get('body_battery', 'N/A')}"""
        
        prompt = f"""{self.SYSTEM_PROMPT}

{context}

# KULLANICI SORUSU
{request.message}"""
        
        response = self.llm.generate(prompt, max_tokens=300)
        
        if debug_info is not None:
            debug_info['context_type'] = 'health_day_status'
            debug_info['target_date'] = str(target_date)
        
        return ChatResponse(
            message=response.text,
            resolved_date=str(target_date),
            debug_metadata=debug_info
        )
    
    def _handle_laps_query(
        self, 
        request: ChatRequest, 
        intent: ParsedIntent,
        pinned_state: PinnedState,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle laps/splits query - requires deep analysis mode."""
        if not pinned_state.is_valid:
            return ChatResponse(
                message="Hangi aktivitenin lap verilerini sorduğunu anlamadım. Önce tarih veya aktivite ismi belirt.",
                debug_metadata=debug_info
            )
        
        # Laps data requires activity_streams which we don't send in normal mode
        return ChatResponse(
            message=f"Lap bazlı analiz için detaylı stream verisi gerekiyor. Bu özellik şu an mevcut değil. "
                    f"Ama {pinned_state.local_start_date} tarihli {pinned_state.activity_name or 'aktivite'} "
                    f"hakkında başka sorular sorabilirsin.",
            resolved_activity_id=pinned_state.garmin_activity_id,
            debug_metadata=debug_info
        )
    
    def _handle_longitudinal_query(
        self, 
        request: ChatRequest, 
        intent: ParsedIntent,
        pinned_state: PinnedState,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle longitudinal prep query (3 months before race, etc.)."""
        anchor_date = intent.anchor_date or (pinned_state.local_start_date if pinned_state.is_valid else None)
        days = intent.trend_days or 90
        
        if not anchor_date:
            return ChatResponse(
                message="Hangi yarış/hedef için hazırlık sürecini sorduğunu anlamadım. "
                        "Önce yarış tarihini belirt (örn: 9 mart 2025 Almada koşusu).",
                debug_metadata=debug_info
            )
        
        # Get summary for the period before anchor date
        start_date = anchor_date - timedelta(days=days)
        
        # Get aggregated data
        summaries = self.repo.get_activity_summaries_range(request.user_id, start_date, anchor_date)
        
        if not summaries:
            return ChatResponse(
                message=f"{anchor_date.strftime('%d %B %Y')} öncesi {days} günlük dönemde aktivite verisi bulamadım.",
                debug_metadata=debug_info
            )
        
        # Build summary
        total_km = sum(s.summary_json.get('distance_km', 0) for s in summaries if s.summary_json)
        total_activities = len(summaries)
        workout_types = {}
        for s in summaries:
            wt = s.workout_type or 'unknown'
            workout_types[wt] = workout_types.get(wt, 0) + 1
        
        context = f"""# HAZIRLIK DÖNEMİ ANALİZİ
ANCHOR_DATE={anchor_date}
PERIOD_DAYS={days}
TOTAL_KM={total_km:.1f}
TOTAL_ACTIVITIES={total_activities}
WORKOUT_DISTRIBUTION={workout_types}
WEEKLY_AVG_KM={total_km / (days / 7):.1f}"""
        
        prompt = f"""{self.SYSTEM_PROMPT}

{context}

# KULLANICI SORUSU
{request.message}"""
        
        response = self.llm.generate(prompt, max_tokens=400)
        
        if debug_info is not None:
            debug_info['context_type'] = 'longitudinal_prep'
            debug_info['anchor_date'] = str(anchor_date)
            debug_info['period_days'] = days
        
        return ChatResponse(
            message=response.text,
            resolved_date=str(anchor_date),
            debug_metadata=debug_info
        )
    
    def _handle_trend_query(
        self, 
        request: ChatRequest, 
        intent: ParsedIntent,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle general trend query."""
        days = intent.trend_days or 28
        context_parts = []
        
        # User model
        user_model = self.repo.get_user_model_json(request.user_id)
        if user_model:
            model_summary = self._summarize_user_model(user_model)
            context_parts.append(f"# KULLANICI MODELİ\n{model_summary}")
        
        # Weekly trend
        weekly_trend = self.repo.get_weekly_trend_text(request.user_id)
        if weekly_trend:
            context_parts.append(f"# HAFTALIK TREND\n{weekly_trend}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""{self.SYSTEM_PROMPT}

{context}

# KULLANICI SORUSU
{request.message}"""
        
        response = self.llm.generate(prompt, max_tokens=400)
        
        if debug_info is not None:
            debug_info['context_type'] = 'trend'
        
        return ChatResponse(message=response.text, debug_metadata=debug_info)
    
    def _handle_last_activity(
        self, 
        request: ChatRequest,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle 'son antrenmanım' intent."""
        activity = self.retriever.get_last_activity(request.user_id)
        
        if not activity:
            return ChatResponse(
                message="Henüz kayıtlı aktivite bulamadım.",
                debug_metadata=debug_info
            )
        
        # Pin this activity
        self.state_manager.pin_activity(
            request.user_id,
            activity.garmin_activity_id,
            activity.local_start_date,
            activity.activity_name,
            'last_activity'
        )
        
        if debug_info is not None:
            debug_info['context_type'] = 'last_activity'
        
        return self._generate_with_activity(request, activity, debug_info)
    
    def _handle_general_query(
        self, 
        request: ChatRequest,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle general query - user model only."""
        context_parts = []
        
        user_model = self.repo.get_user_model_json(request.user_id)
        if user_model:
            model_summary = self._summarize_user_model(user_model)
            context_parts.append(f"# KULLANICI MODELİ\n{model_summary}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""{self.SYSTEM_PROMPT}

{context}

# KULLANICI SORUSU
{request.message}"""
        
        response = self.llm.generate(prompt, max_tokens=300)
        
        if debug_info is not None:
            debug_info['context_type'] = 'general'
        
        return ChatResponse(message=response.text, debug_metadata=debug_info)
    
    def _handle_resolution(
        self, 
        request: ChatRequest, 
        resolution: Resolution,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle resolution result."""
        if resolution.status in ('not_found', 'needs_clarification'):
            return ChatResponse(
                message=resolution.clarification_message,
                debug_metadata=debug_info
            )
        return ChatResponse(message="Beklenmeyen durum.", debug_metadata=debug_info)
    
    def _handle_specific_activity(
        self, 
        request: ChatRequest,
        garmin_activity_id: int,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Handle when specific activity ID is provided."""
        summary = self.repo.get_activity_summary(request.user_id, garmin_activity_id)
        
        if not summary:
            return ChatResponse(
                message=f"Bu aktivite ID'si ({garmin_activity_id}) için veri bulamadım.",
                debug_metadata=debug_info
            )
        
        activity = ActivityCandidate(
            garmin_activity_id=summary.garmin_activity_id,
            activity_name="",
            local_start_date=summary.local_start_date,
            distance_km=summary.summary_json.get('distance_km', 0) if summary.summary_json else 0,
            duration_min=summary.summary_json.get('duration_min', 0) if summary.summary_json else 0,
            workout_type=summary.workout_type,
            facts_text=summary.facts_text,
            summary_text=summary.summary_text
        )
        
        return self._generate_with_activity(request, activity, debug_info)
    
    def _generate_with_activity(
        self, 
        request: ChatRequest, 
        activity: ActivityCandidate,
        debug_info: Optional[Dict]
    ) -> ChatResponse:
        """Generate response with a specific activity in context."""
        context_parts = []
        
        if activity.facts_text:
            context_parts.append(f"# AKTİVİTE VERİLERİ\n{activity.facts_text}")
        
        if activity.summary_text:
            context_parts.append(f"# ÖZET\n{activity.summary_text}")
        
        user_model = self.repo.get_user_model_json(request.user_id)
        if user_model:
            model_summary = self._summarize_user_model(user_model)
            context_parts.append(f"# KULLANICI MODELİ\n{model_summary}")
        
        context = "\n\n".join(context_parts)
        
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS]
        
        if debug_info is not None:
            debug_info['context_type'] = 'specific_activity'
            debug_info['activity_id'] = activity.garmin_activity_id
            debug_info['context_chars'] = len(context)
        
        prompt = f"""{self.SYSTEM_PROMPT}

{context}

# KULLANICI SORUSU
{request.message}"""
        
        response = self.llm.generate(prompt, max_tokens=400)
        
        return ChatResponse(
            message=response.text,
            resolved_activity_id=activity.garmin_activity_id,
            resolved_date=str(activity.local_start_date),
            debug_metadata=debug_info
        )
    
    def _summarize_user_model(self, model_json: Dict) -> str:
        """Extract key info from user model for context."""
        parts = []
        if 'weekly_avg_km' in model_json:
            parts.append(f"WEEKLY_AVG_KM={model_json['weekly_avg_km']}")
        if 'injury_risk' in model_json:
            parts.append(f"INJURY_RISK={model_json['injury_risk']}")
        if 'training_consistency' in model_json:
            parts.append(f"CONSISTENCY={model_json['training_consistency']}")
        return "\n".join(parts) if parts else "No user model data"
    
    def _get_health_for_date(self, user_id: int, target_date: date) -> Optional[Dict]:
        """Get health/biometrics data for a specific date from existing tables."""
        health_data = {}
        
        # Query sleep_logs
        try:
            sleep_result = self.db.execute(text("""
                SELECT sleep_score, duration_seconds, deep_seconds, rem_seconds
                FROM sleep_logs
                WHERE user_id = :user_id AND calendar_date = :target_date
            """), {'user_id': user_id, 'target_date': target_date}).fetchone()
            
            if sleep_result:
                health_data['sleep_score'] = sleep_result[0]
                hours = (sleep_result[1] or 0) / 3600
                health_data['sleep_hours'] = round(hours, 1)
        except:
            pass
        
        # Query hrv_logs
        try:
            hrv_result = self.db.execute(text("""
                SELECT last_night_avg, status
                FROM hrv_logs
                WHERE user_id = :user_id AND calendar_date = :target_date
            """), {'user_id': user_id, 'target_date': target_date}).fetchone()
            
            if hrv_result:
                health_data['hrv'] = hrv_result[0]
                health_data['hrv_status'] = hrv_result[1]
        except:
            pass
        
        # Query stress_logs (if exists)
        try:
            stress_result = self.db.execute(text("""
                SELECT avg_stress_level
                FROM stress_logs
                WHERE user_id = :user_id AND calendar_date = :target_date
            """), {'user_id': user_id, 'target_date': target_date}).fetchone()
            
            if stress_result:
                health_data['stress_level'] = stress_result[0]
        except:
            pass
        
        if health_data:
            return health_data
        
        # Fallback to 7-day average from coach_v2 view
        try:
            result = self.db.execute(text("""
                SELECT avg_sleep_score, avg_hrv, avg_stress
                FROM coach_v2.v_biometrics_7d
                WHERE user_id = :user_id
            """), {'user_id': user_id}).fetchone()
            
            if result:
                return {
                    'sleep_score': float(result[0]) if result[0] else None,
                    'hrv': float(result[1]) if result[1] else None,
                    'stress_level': float(result[2]) if result[2] else None,
                    'note': '7-day average (specific date not found)'
                }
        except:
            pass
        
        return None

