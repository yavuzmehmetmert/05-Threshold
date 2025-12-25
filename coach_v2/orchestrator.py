"""
Coach V2 Orchestrator (Humanized Rewrite)
==========================================

A conversational, memory-aware running coach with deep expertise.
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging
import re
import google.generativeai as genai

from coach_v2.repository import CoachV2Repository
from coach_v2.llm_client import LLMClient, LLMResponse
from coach_v2.query_understanding import parse_user_query, ParsedIntent, PinnedState
from coach_v2.candidate_retrieval import CandidateRetriever, Resolution, ActivityCandidate
from coach_v2.training_load_engine import TrainingLoadEngine
from coach_v2.analysis_pack_builder import AnalysisPackBuilder
from coach_v2.targeted_extraction import TargetedExtractor
from coach_v2.evidence_gate import EvidenceGate
from coach_v2.performance_analyzer import PerformanceAnalyzer
from coach_v2.athlete_memory import AthleteMemoryStore
from coach_v2.sql_agent import SQLAgent
from coach_v2.intent_classifier import (
    IntentClassifier, classify_intent, classify_intent_with_debug, 
    classify_intent_full, classify_intent_full_with_debug, IntentResult
)
from coach_v2.planner import (
    Planner, create_execution_plan, create_execution_plan_with_debug,
    ExecutionPlan, ActionStep
)
from coach_v2.state import conversation_state_manager, ConversationState

# ==============================================================================
# CONTEXT BOUNDS
# ==============================================================================
MAX_CONTEXT_CHARS = 6000


@dataclass
class ChatRequest:
    """Chat request from user."""
    user_id: int
    message: str
    garmin_activity_id: Optional[int] = None
    deep_analysis_mode: bool = False
    debug: bool = False
    conversation_history: List[tuple] = None
    activity_details_json: Optional[Dict[str, Any]] = None
    
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
    debug_steps: Optional[List[Dict[str, Any]]] = None  # Step-by-step debug


def get_persona_modifier(tsb: float) -> str:
    """
    Get proactive persona modifier based on athlete's TSB.
    
    Args:
        tsb: Training Stress Balance (CTL - ATL). 
             Positive = rested, Negative = fatigued.
    
    Returns:
        Persona modifier string to inject into prompts.
    """
    if tsb < -20:
        return """
SPORCU DURUMU: YORGUN (TSB < -20)
- Nazik ve koruyucu ol. Sporcunun yorgun olduğunu anla.
- Ağır antrenman önerme. Recovery'ye odaklan.
- "Dinlensen iyi olur" gibi yumuşak öneriler ver.
"""
    elif tsb > 10:
        return """
SPORCU DURUMU: DİNLENMİŞ (TSB > 10)
- Meydan oku! Sporcu hazır.
- "Daha fazlasını verebilirsin" de.
- Yoğun antrenman veya yarış önerilebilir.
"""
    return ""  # Normal TSB range (-20 to +10)


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
    Humanized, conversational running coach with memory and expertise.
    """
    
    # =========================================================================
    # PERSONA & KNOWLEDGE
    # =========================================================================
    
    COACH_PERSONA = """*DISCLAIMER: I am a sports data analysis expert. I am NOT a medical professional or a doctor. I analyze athletic metrics for performance insights. I do not provide medical diagnoses or health treatments.*

KİMLİK VE TON:
- İsmin: hOCA.
- Rolün: 15+ yıllık tecrübeli atletik veri analisti ve koşu uzmanı.
- Tarzın: Domenico Tedesco gibi; düşünceli, doğrudan ve analitik. Gereksiz heyecan gösterme.
- Dil: "Sen" dili kullan. Samimi ama profesyonel.
- Yapı: Kısa cümleler. Paragrafları gereksiz uzatma ama sporcunun ihtiyacı olan detayı ver.
- Soru Sorma: Sadece gerçekten cevaba ihtiyacın varsa sor. Gereksiz "Başka sorun var mı?" gibi cümlelerden kaçın.

NEGATIVE RULES (CRITICAL):
- NO MARKDOWN: Do NOT use bold (**), italic (*), or headers (#).
- NO BOLD: Never use double asterisks.
- NO ITALIC: Never use single asterisks or underscores for emphasis.
- PLAIN TEXT ONLY: All outputs must be raw plain text.
- Headings: Use ALL CAPS for headers instead of bolding.
- Links: Activity links [Name](activity://id) are the ONLY allowed markdown format.

ANALİZ PRENSİPLERİ:
- Sayıları ezberletme, sporcunun hissettiği eforla bağlantısını kur.
- Veride teknik hata ("0", "None") varsa sporcuyu eleştirme, pas geç.
- Boş övgü yapma, veriye dayanarak kanıtla.
- Aktiviteden bahsederken MUTLAKA isim, link ve tarih kullan: [İsim (Gün Ay)](activity://ACTIVITY_ID)
"""

    RUNNING_EXPERTISE = """
GELİŞMİŞ ANALİZ MANTIĞI (BU SIRAYI İZLE):

1. VERİ KORELASYONU (Decoupling Analizi):
   - Metriklere tek tek bakma, birbirleriyle ilişkisini kur.
   - Power vs Pace: Power artıyor ama Pace sabit/düşüyorsa; koşu ekonomisi bozulmuş, yorgunluk başlamış.
   - Nabız vs Pace (Cardiac Drift): Pace sabitken Nabız sonlara doğru orantısız artıyorsa; dehidrasyon veya aerobik dayanıklılık eksikliği.

2. BAĞLAM FARKINDALIĞI:
   - Lokasyon: Aktivite ismi "Kadıköy", "Şehir", "Cadde" içeriyorsa; ani pace düşüşlerini yorgunluğa değil, trafik ışığına yor. "Işıklara takıldığını görüyorum" de.
   - Hava Durumu: Rüzgar veya yüksek nem varsa, pace düşüklüğünü buna bağla.

3. BİYOMEKANİK & TEKNİK:
   - Ezbere Konuşma: Spesifik kadans sayısı (örn: 180) dayatma. Her koşucunun anatomisi farklı.
   - Overstriding Tehlikesi: Asla "adımını uzat" tavsiyesi verme. Yanlış anlaşılır ve sakatlık yapar.
   - Doğru Yönlendirme: Hızlanmak için adım uzatmak yerine "yerden güçlü itiş" (Power) veya "kadans artışı" öner.
   - Dikey Salınım: Çok düşükse (sürünerek) veya çok yüksekse (zıplayarak) uyar, yoksa pas geç.

4. VERİ TEMİZLİĞİ (Son Lap Kuralı):
   - ÇOK ÖNEMLİ: Son tur 30 saniyeden kısa veya 100 metreden azsa; TAMAMEN GÖRMEZDEN GEL.
   - Bu, sporcunun saati durdururken geçirdiği ölü zamandır.

5. YÜKLENME VE FORM (CTL/TSB):
   - TSB negatifse (-10, -20) ve performans kötüyse: "Yorgun bacaklarla savaşıyorsun, normaldir."
   - TSB pozitifse (+5, +15) ve performans iyiyse: "Taper işe yaramış, bacakların taze."

REFERANS BİLGİLERİ:

Nabız Bölgeleri:
- Zone 2: Recovery/Base (Konuşulabilir)
- Zone 3: Tempo (Comfortably Hard)
- Zone 4: Threshold (Laktat Eşiği - Sürdürülebilir acı)
- Zone 5: VO2max (Max efor)

Pace Rehberi:
- Easy: Maraton pace + 60-90sn
- Tempo: Yarı Maraton pace
- Threshold: 10K pace
- Interval: 5K pace veya daha hızlı

Metrikler:
- TSB (Form): Pozitif = Dinlenmiş, Negatif = Yorgun/Yükleme döneminde.
- Power (Watt): Koşu gücü. Rüzgar/eğimden bağımsız efor göstergesi.
- Negatif Split: Yarışın ikinci yarısını daha hızlı koşmak (İdeal strateji).
"""

    GREETING_RESPONSE = """Selam! 👋 

Bugün antrenmanını değerlendirebiliriz, haftalık yüklenmeye bakabiliriz, ya da aklındaki herhangi bir konuyu konuşabiliriz. Hazır olduğunda başlayalım."""

    NO_DATA_RESPONSE = """Şu an elimde analiz edecek veri yok. 

Birkaç seçenek var:
- "Son koşumu analiz et" diyebilirsin
- Belirli bir tarih sorabilirsin (örn: "3 Aralık'taki koşu")
- Ya da formun hakkında konuşabiliriz (örn: "Bu hafta nasıldı?")"""

    FAREWELL_RESPONSE = """Görüşürüz! 👋 

Bir sonraki antrenmanda burada olacağım."""

    def __init__(self, db: Session, llm_client: LLMClient):
        self.db = db
        self.repo = CoachV2Repository(db)
        
        # Split models: Fast for routing, Strong for reasoning
        # gemini-2.0-flash-exp is the best high-tier model that doesn't block sports data.
        # gemini-3-pro-preview is used in Planner correctly, but blocks Analysis.
        strong_model_name = "gemini-2.0-flash-exp"
        fast_model_name = "gemini-2.0-flash"
        
        # Inject persona as system instruction for Gemini models
        from coach_v2.llm_client import GeminiClient
        system_prompt = f"{self.COACH_PERSONA}\n\n{self.RUNNING_EXPERTISE}"
        
        # Main LLM for response and analysis (Strong)
        self.llm = GeminiClient(
            api_key=llm_client.api_key, 
            model=strong_model_name, 
            system_instruction=system_prompt
        )
            
        self.retriever = CandidateRetriever(db)
        self.state_manager = ConversationStateManager(db)
        
        # Explicit fast classifier
        from coach_v2.intent_classifier import IntentClassifier
        self.intent_classifier_obj = IntentClassifier(api_key=llm_client.api_key)
        # Force Flash for intent classification
        self.intent_classifier_obj.model = genai.GenerativeModel(fast_model_name)
        
        self.load_engine = TrainingLoadEngine(db)
        self.pack_builder = AnalysisPackBuilder()
        self.extractor = TargetedExtractor()
        self.evidence_gate = EvidenceGate()
        self.performance_analyzer = PerformanceAnalyzer(db)
        self.memory_store = AthleteMemoryStore(db)
        
        # SQL Agent also uses the strong model for better SQL generation
        self.sql_agent = SQLAgent(db, self.llm)

    def _clean_markdown(self, text: str) -> str:
        """
        Forcefully removes bold and italic markdown from responses.
        Preserves activity links [X](activity://Y).
        """
        if not text:
            return ""
        
        # 1. Remove bold (**)
        text = text.replace("**", "")
        # 2. Remove italic (*) - but be careful of list markers if needed
        # We'll replace them with empty if they surround text
        text = re.sub(r'(?<!\\)\*', '', text)
        # 3. Remove underscores for italic (__ or _)
        text = text.replace("__", "")
        # We only remove single underscores if they are likely formatting (flanked by non-alpha)
        # but honestly, standard running data has underscores in IDs, so we be careful.
        # Simple approach: user wants NO markdown, let's just strip most common bold/italic.
        
        # 4. Remove headers (#)
        text = re.sub(r'^(#+)\s*', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle chat request with AI Planner for multi-action execution.
        
        Flow:
        1. Create ExecutionPlan (list of actions)
        2. Execute each action in sequence
        3. Pass results between handlers
        4. Return final combined response
        """
        debug_info = {} if request.debug else None
        debug_steps = [] if request.debug else None
        
        # 0. Get or create conversation state for this user
        conv_state = conversation_state_manager.get_or_create(request.user_id, self.db)
        
        # Add user message to history
        conv_state.add_turn("user", request.message)
        
        # Update metrics if stale (more than 5 min old)
        if (conv_state.metrics.last_updated is None or 
            (datetime.now() - conv_state.metrics.last_updated).seconds > 300):
            conv_state.update_metrics_from_db(self.db)
        
        # 1. Create Execution Plan (AI Planner)
        history_for_planner = conv_state.get_history_for_prompt()
        metrics_context = conv_state.get_metrics_summary()
        
        plan, planner_debug = create_execution_plan_with_debug(
            request.message, 
            history_for_planner,
            metrics_context
        )
        
        # 2. Compute proactive persona based on TSB
        tsb = conv_state.metrics.tsb
        persona_modifier = get_persona_modifier(tsb)
        
        if request.debug:
            debug_info['planner_thought'] = plan.thought_process
            debug_info['planner_debug'] = planner_debug
            debug_info['plan_step_count'] = plan.step_count
            debug_info['plan_needs_input'] = plan.needs_user_input
            debug_info['conversation_history_count'] = len(conv_state.history)
            debug_info['user_tsb'] = tsb
            debug_info['persona_modifier'] = 'YORGUN' if tsb < -20 else ('DİNLENMİŞ' if tsb > 10 else 'NORMAL')
            
            # Show planner output
            model_used = planner_debug.get('model', 'unknown')
            if 'fallback' in model_used.lower():
                source_description = f"⚠️ Fallback → {plan.step_count} step(s)"
            else:
                source_description = f"✅ {model_used} → {plan.step_count} step(s) (conf: {plan.confidence:.0%})"
            
            # Build detailed plan visualization
            plan_visualization = []
            for i, s in enumerate(plan.steps):
                step_info = {
                    "step": i + 1,
                    "handler": s.handler,
                    "description": s.entities.get('description', f"Execute {s.handler}"),
                    "entities": s.entities,
                    "depends_on": getattr(s, 'depends_on', None)
                }
                if s.requires_input:
                    step_info["requires_user_input"] = True
                    step_info["input_question"] = s.input_prompt
                plan_visualization.append(step_info)
            
            debug_steps.append({
                "step": 0,
                "name": "📋 EXECUTION PLAN",
                "status": f"{plan.step_count} step(s) planned",
                "description": source_description,
                "thought_process": plan.thought_process,
                "plan": plan_visualization,
                "persona_mode": debug_info.get('persona_modifier')
            })
        
        # 3. Get pinned state for activity context
        pinned_state = self.state_manager.get_pinned_state(request.user_id)
        
        if debug_info is not None:
            debug_info['pinned_activity_id'] = pinned_state.garmin_activity_id if pinned_state else None
        
        # 4. Execute plan (sequential handler execution)
        response = self._execute_plan(
            request, plan, pinned_state, debug_info, debug_steps,
            persona_modifier=persona_modifier, conv_state=conv_state
        )
        
        # 5. Add assistant response to conversation history
        final_handler = plan.steps[-1].handler if plan.steps else "unknown"
        conv_state.add_turn("assistant", response.message, handler_type=final_handler)
        
        return response
    
    def _execute_plan(
        self, 
        request, 
        plan: ExecutionPlan,
        pinned_state,
        debug_info,
        debug_steps,
        persona_modifier: str = "",
        conv_state: ConversationState = None
    ) -> ChatResponse:
        """
        Execute an ExecutionPlan sequentially.
        
        Passes results between handlers for context.
        Captures raw data from each step for debugging.
        """
        execution_results = []  # Results from each step with raw data
        
        for i, step in enumerate(plan.steps):
            step_num = i + 1
            
            # Pre-execution debug entry
            step_debug_entry = {
                "step": step_num,
                "name": f"Execute: {step.handler}",
                "status": "running",
                "description": f"Step {step_num}/{plan.step_count}: {step.handler}",
                "entities": step.entities
            }
            if debug_steps is not None:
                debug_steps.append(step_debug_entry)
            
            # Execute this handler and capture result + raw data
            result, raw_data = self._execute_single_handler_with_data(
                request=request,
                handler_type=step.handler,
                entities=step.entities,
                pinned_state=pinned_state,
                debug_info=debug_info,
                debug_steps=debug_steps,
                persona_modifier=persona_modifier,
                conv_state=conv_state,
                previous_results=execution_results
            )
            
            # Store both message and raw data for next handlers
            step_result = {
                "handler": step.handler,
                "step": step_num,
                "result": result.message if result else None,
                "raw_data": raw_data  # Full data context (activity, health, etc.)
            }
            execution_results.append(step_result)
            
            # Add fetched data to debug (detailed view)
            if debug_steps is not None and raw_data:
                debug_steps.append({
                    "step": step_num,
                    "name": "📊 Data Fetched",
                    "status": "success",
                    "description": f"Step {step_num} data",
                    "data_summary": self._summarize_raw_data(raw_data),
                    "raw_data_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else None,
                    # Detailed data preview
                    "data_preview": self._format_data_preview(raw_data)
                })
            
            # Merge handler's debug_steps into our main debug_steps
            if debug_steps is not None and result and result.debug_steps:
                for handler_step in result.debug_steps:
                    # Avoid duplicating already-added steps
                    if handler_step not in debug_steps:
                        debug_steps.append(handler_step)
            
            # If this step requires user input, return immediately with question
            if step.requires_input and step.input_prompt:
                return ChatResponse(
                    message=step.input_prompt,
                    debug_metadata=debug_info,
                    debug_steps=debug_steps
                )
            
            # If this is the last step, return with merged debug_steps
            if i == len(plan.steps) - 1:
                return ChatResponse(
                    message=result.message if result else self.NO_DATA_RESPONSE,
                    debug_metadata=debug_info,
                    debug_steps=debug_steps
                )
        
        # Fallback if no steps
        return ChatResponse(
            message=self.NO_DATA_RESPONSE,
            debug_metadata=debug_info,
            debug_steps=debug_steps
        )
    
    def _execute_single_handler_with_data(
        self,
        request,
        handler_type: str,
        entities: Dict[str, Any],
        pinned_state,
        debug_info,
        debug_steps,
        persona_modifier: str,
        conv_state: ConversationState,
        previous_results: List[Dict] = None
    ) -> Tuple[ChatResponse, Optional[Dict]]:
        """
        Execute a single handler with context from previous results.
        
        Returns:
            Tuple of (ChatResponse, raw_data_dict)
            raw_data_dict contains the fetched data for debugging and passing to next handlers
        """
        raw_data = None
        
        # Build comprehensive context from previous handler results
        if previous_results and handler_type in ["sohbet_handler"]:
            # Build context with both message and raw data
            context_parts = []
            for r in previous_results:
                if r.get('raw_data'):
                    # Use raw_data for full context
                    data = r['raw_data']
                    context_parts.append(f"=== {r['handler']} (Step {r.get('step', '?')}) ===\n{self._format_raw_data_for_context(data)}")
                elif r.get('result'):
                    # Fallback to message
                    context_parts.append(f"[{r['handler']}]: {r['result'][:500]}")
            
            context_from_previous = "\n\n".join(context_parts)
            entities = entities.copy()
            entities['previous_context'] = context_from_previous
        
        # Route to appropriate handler and capture raw data
        result = self._route_by_handler(
            request, handler_type, pinned_state, debug_info, debug_steps,
            entities=entities, persona_modifier=persona_modifier, conv_state=conv_state,
            previous_results=previous_results
        )
        
        # Extract raw_data from result if available (set by handlers)
        if hasattr(result, 'raw_data'):
            raw_data = result.raw_data
        elif debug_info and 'last_handler_data' in debug_info:
            raw_data = debug_info.pop('last_handler_data')
        
        return result, raw_data
    
    def _summarize_raw_data(self, raw_data: Dict) -> str:
        """Summarize raw data for debug display."""
        if not raw_data:
            return "No data"
        
        summary_parts = []
        
        # Activity info
        if 'activity' in raw_data:
            act = raw_data['activity']
            summary_parts.append(f"📍 {act.get('name', 'Activity')} ({act.get('date', '')})")
            if 'distance_km' in act:
                summary_parts.append(f"🏃 {act['distance_km']:.1f}km")
            if 'avg_pace' in act:
                summary_parts.append(f"⏱️ Pace: {act['avg_pace']}")
            if 'avg_hr' in act:
                summary_parts.append(f"❤️ HR: {act['avg_hr']}bpm")
        
        # Health data
        if 'health' in raw_data:
            health = raw_data['health']
            if health.get('hrv'):
                summary_parts.append(f"💓 HRV: {health['hrv']}ms")
            if health.get('sleep_score'):
                summary_parts.append(f"😴 Sleep: {health['sleep_score']}")
            if health.get('stress'):
                summary_parts.append(f"😰 Stress: {health['stress']}")
        
        # Training load
        if 'training_load' in raw_data:
            tl = raw_data['training_load']
            if tl.get('tsb') is not None:
                summary_parts.append(f"📊 TSB: {tl['tsb']:.1f}")
        
        return " | ".join(summary_parts) if summary_parts else str(list(raw_data.keys()))
    
    def _format_raw_data_for_context(self, raw_data: Dict) -> str:
        """Format raw data as context string for LLM."""
        if not raw_data:
            return ""
        
        # If full_context_string is available, use it directly (built by _build_activity_context)
        if 'full_context_string' in raw_data and raw_data['full_context_string']:
            return raw_data['full_context_string']
        
        lines = []
        
        if 'activity' in raw_data:
            act = raw_data['activity']
            lines.append(f"Aktivite: {act.get('name', 'Unknown')}")
            lines.append(f"Tarih: {act.get('date', 'Unknown')}")
            if 'distance_km' in act:
                lines.append(f"Mesafe: {act['distance_km']:.2f} km")
            if 'duration' in act:
                lines.append(f"Süre: {act['duration']}")
            if 'avg_pace' in act:
                lines.append(f"Ortalama Pace: {act['avg_pace']}")
            if 'avg_hr' in act:
                lines.append(f"Ortalama Nabız: {act['avg_hr']} bpm")
            if 'elevation_gain' in act:
                lines.append(f"Yükseliş: {act['elevation_gain']}m")
        
        if 'health' in raw_data:
            health = raw_data['health']
            lines.append("\nSağlık Verileri:")
            if health.get('hrv'):
                lines.append(f"- HRV: {health['hrv']} ms")
            if health.get('sleep_score'):
                lines.append(f"- Uyku Skoru: {health['sleep_score']}")
            if health.get('sleep_duration'):
                lines.append(f"- Uyku Süresi: {health['sleep_duration']}")
            if health.get('stress'):
                lines.append(f"- Stres: {health['stress']}")
        
        if 'training_load' in raw_data:
            tl = raw_data['training_load']
            lines.append("\nAntrenman Yükü:")
            if tl.get('ctl') is not None:
                lines.append(f"- CTL (Fitness): {tl['ctl']:.1f}")
            if tl.get('atl') is not None:
                lines.append(f"- ATL (Yorgunluk): {tl['atl']:.1f}")
            if tl.get('tsb') is not None:
                lines.append(f"- TSB (Form): {tl['tsb']:.1f}")
        
        if 'laps' in raw_data and raw_data['laps']:
            lines.append(f"\nTurlar ({len(raw_data['laps'])} tur):")
            for lap in raw_data['laps'][:5]:  # First 5 laps
                lines.append(f"  - {lap.get('distance_km', '?')}km @ {lap.get('pace', '?')}")
        
        return "\n".join(lines)
    
    def _format_data_preview(self, raw_data: Dict) -> str:
        """Format raw data as detailed table-like preview for debug output."""
        if not raw_data:
            return "No data"
        
        lines = []
        
        # Activity table header
        if 'activity' in raw_data:
            act = raw_data['activity']
            lines.append("┌─────────────────── ACTIVITY ───────────────────┐")
            lines.append(f"│ ID:       {act.get('id', 'N/A')}")
            lines.append(f"│ Name:     {act.get('name', 'Unknown')}")
            lines.append(f"│ Date:     {act.get('date', 'N/A')}")
            if act.get('distance_km'):
                lines.append(f"│ Distance: {act['distance_km']:.2f} km")
            if act.get('duration'):
                lines.append(f"│ Duration: {act['duration']}")
            if act.get('avg_pace'):
                lines.append(f"│ Avg Pace: {act['avg_pace']}")
            if act.get('avg_hr'):
                lines.append(f"│ Avg HR:   {act['avg_hr']} bpm")
            if act.get('elevation_gain'):
                lines.append(f"│ Elevation: {act['elevation_gain']}m")
            lines.append("└────────────────────────────────────────────────┘")
        
        # Health data table
        if 'health' in raw_data and raw_data['health']:
            health = raw_data['health']
            lines.append("")
            lines.append("┌─────────────────── HEALTH ────────────────────┐")
            if health.get('hrv'):
                lines.append(f"│ HRV (last night): {health['hrv']} ms")
            if health.get('sleep_score'):
                lines.append(f"│ Sleep Score:      {health['sleep_score']}")
            if health.get('sleep_duration'):
                lines.append(f"│ Sleep Duration:   {health['sleep_duration']}")
            if health.get('stress'):
                lines.append(f"│ Stress Level:     {health['stress']}")
            lines.append("└────────────────────────────────────────────────┘")
        
        # Training load table
        if 'training_load' in raw_data and raw_data['training_load']:
            tl = raw_data['training_load']
            lines.append("")
            lines.append("┌─────────────── TRAINING LOAD ─────────────────┐")
            if tl.get('ctl') is not None:
                lines.append(f"│ CTL (Fitness):   {tl['ctl']:.1f}")
            if tl.get('atl') is not None:
                lines.append(f"│ ATL (Fatigue):   {tl['atl']:.1f}")
            if tl.get('tsb') is not None:
                lines.append(f"│ TSB (Form):      {tl['tsb']:.1f}")
            lines.append("└────────────────────────────────────────────────┘")
        
        # Lap splits table (first 5)
        if 'laps' in raw_data and raw_data['laps']:
            laps = raw_data['laps']
            lines.append("")
            lines.append(f"┌───────────────── LAPS ({len(laps)} total) ─────────────────┐")
            lines.append("│ Lap │ Distance │  Pace  │")
            lines.append("├─────┼──────────┼────────┤")
            for i, lap in enumerate(laps[:5], 1):
                dist = lap.get('distance_km', '?')
                pace = lap.get('pace', '?')
                lines.append(f"│  {i}  │ {dist:>7}km │ {pace:>6} │")
            if len(laps) > 5:
                lines.append(f"│ ... │  ({len(laps)-5} more laps)  │")
            lines.append("└─────┴──────────┴────────┘")
        
        return "\n".join(lines)
    
    # =========================================================================
    # AI-BASED HANDLER ROUTING
    # =========================================================================
    
    SMALL_TALK_RESPONSE = """İyiyim, teşekkürler. 💪

Son koşunu analiz edebilirim ya da haftalık durumuna bakabiliriz. Hazır olduğunda söyle."""

    def _route_by_handler(
        self, 
        request, 
        handler_type: str, 
        pinned_state, 
        debug_info, 
        debug_steps=None,
        entities: Dict[str, Any] = None,
        persona_modifier: str = "",
        conv_state: ConversationState = None,
        previous_results: List[Dict] = None
    ):
        """
        Route to handler based on AI classification.
        
        Args:
            request: ChatRequest
            handler_type: Handler name from IntentClassifier
            pinned_state: Pinned activity context
            debug_info: Debug metadata dict
            debug_steps: Debug step list
            entities: Extracted entities (date, metric, etc.)
            persona_modifier: TSB-based persona adjustment
            conv_state: Current conversation state
        """
        if entities is None:
            entities = {}
        
        if debug_info is not None:
            debug_info['handler_routed'] = handler_type
        
        # Initialize debug_steps if needed
        if debug_steps is None:
            debug_steps = []
        
        # STATIC RESPONSES (no LLM needed)
        if handler_type == "welcome_intent":
            debug_steps.append({"step": 1, "name": "Handler", "status": "Static Response", "description": "Selamlama cevabı"})
            return ChatResponse(
                message=self.GREETING_RESPONSE,
                debug_metadata=debug_info,
                debug_steps=debug_steps
            )
        
        if handler_type == "small_talk_intent":
            debug_steps.append({"step": 1, "name": "Handler", "status": "Static Response", "description": "Small talk cevabı"})
            return ChatResponse(
                message=self.SMALL_TALK_RESPONSE,
                debug_metadata=debug_info,
                debug_steps=debug_steps
            )
        
        if handler_type == "farewell_intent":
            debug_steps.append({"step": 1, "name": "Handler", "status": "Static Response", "description": "Veda cevabı"})
            return ChatResponse(
                message=self.FAREWELL_RESPONSE,
                debug_metadata=debug_info,
                debug_steps=debug_steps
            )
        
        # LLM-BASED HANDLERS
        if handler_type == "training_detail_handler":
            debug_steps.append({"step": 1, "name": "Handler", "status": "training_detail_handler", "description": f"Aktivite analizi (entities: {entities})"})
            # Get activity based on entities (date, activity_ref)
            return self._handle_training_detail(request, pinned_state, debug_info, debug_steps, entities=entities, previous_results=previous_results)
        
        if handler_type == "db_handler":
            debug_steps.append({"step": 1, "name": "Handler", "status": "db_handler", "description": f"SQL Agent sorgusu (entities: {entities})"})
            # SQL Agent for database queries using entities
            return self._handle_general_query(request, debug_info, debug_steps, entities=entities)
        
        if handler_type == "sohbet_handler":
            debug_steps.append({"step": 1, "name": "Handler", "status": "sohbet_handler", "description": "Genel sohbet (LLM)"})
            # Direct LLM conversation with context from previous handlers
            return self._handle_sohbet(request, debug_info, debug_steps, persona_modifier=persona_modifier, conv_state=conv_state, entities=entities)
    
    def _handle_sohbet(self, request, debug_info, debug_steps=None, persona_modifier: str = "", conv_state: ConversationState = None, entities: Dict[str, Any] = None):
        """Handle general conversation with LLM - may include context from previous handlers."""
        if entities is None:
            entities = {}
        
        try:
            # Build context with metrics if available
            metrics_context = ""
            if conv_state and conv_state.metrics.last_updated:
                metrics_context = conv_state.get_metrics_summary()
            
            # Get previous handler results (multi-step execution context)
            previous_context = entities.get('previous_context', '')
            has_data_context = bool(previous_context)
            
            if has_data_context:
                # Multi-step mode: analyze data from previous handlers
                prompt = f"""{persona_modifier}

{metrics_context}

# ÖNCEKİ ADIMLARDAN GELEN VERİLER
Aşağıdaki veriler veritabanından çekildi:

{previous_context}

# GÖREV
Yukarıdaki verileri analiz edip sporcuya açıkla.
- Verileri karşılaştır, önemli farkları vurgula.
- Koçluk tavsiyesi ver.
- Tedesco tarzı: Net, doğrudan, gerekçeli.

SPORCU SORUSU: {request.message}
"""
            else:
                # Simple sohbet mode: no data context
                prompt = f"""{self.COACH_PERSONA}

{self.RUNNING_EXPERTISE}

{persona_modifier}

{metrics_context}

# SOHBET KURALLARI
Sporcu sana genel bir soru soruyor veya sohbet etmek istiyor.
- Samimi, kısa ve net cevap ver.
- Tedesco tarzı: Düşünceli, doğrudan, gereksiz soru sorma.
- Eğer spesifik veri lazımsa öneri sun ama soru şeklinde değil.

SPORCU MESAJI: {request.message}
"""
            
            response = self.llm.generate(prompt, max_tokens=800 if has_data_context else 500, temperature=0.7)
            clean_text = self._clean_markdown(response.text)
            
            # Map LLMResponse back with clean text
            response = LLMResponse(
                text=clean_text, 
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                model=response.model
            )
            
            if debug_steps:
                debug_steps.append({
                    "step": 2, 
                    "name": "LLM Sohbet", 
                    "status": "success",
                    "description": f"LLM cevabı ({'Veri analizi' if has_data_context else 'Sohbet'})",
                    "has_data_context": has_data_context,
                    # Full prompt sent to LLM (no truncation - frontend scrolls)
                    "prompt_sent": prompt,
                    # Previous context (no truncation - frontend scrolls)
                    "previous_context_preview": previous_context if previous_context else None
                })
            
            return ChatResponse(
                message=response.text,
                debug_metadata=debug_info,
                debug_steps=debug_steps or []
            )
        except Exception as e:
            logging.error(f"Sohbet handler failed: {e}")
            return ChatResponse(
                message="Şu an sohbet edemiyorum, teknik bir sorun var.",
                debug_metadata=debug_info,
                debug_steps=debug_steps or []
            )
    
    def _handle_training_detail(self, request, pinned_state, debug_info, debug_steps=None, entities: Dict[str, Any] = None, previous_results: List[Dict] = None):
        """
        Handle training detail requests - fetch activity based on entities.
        
        Entities can include:
        - date: "yesterday", "today", "last_week", or specific date
        - activity_ref: "last", "this", "previous", "today", "yesterday"
        - metric: "pace", "hr", "power" for focused analysis
        - use_previous_activity: True - use activity_id from previous handler (lookup pattern)
        
        Returns ChatResponse and stores raw_data in debug_info for handler chaining.
        """
        if entities is None:
            entities = {}
        if previous_results is None:
            previous_results = []
        
        # CHECK FOR USE_PREVIOUS_ACTIVITY: Get activity from previous lookup handler
        if entities.get('use_previous_activity') and previous_results:
            # Find found_activity from previous handler results
            for prev in reversed(previous_results):  # Check most recent first
                raw_data = prev.get('raw_data', {})
                if 'found_activity' in raw_data:
                    found = raw_data['found_activity']
                    activity_id = found.get('activity_id')
                    if activity_id:
                        # Fetch activity by ID
                        import models
                        activity = self.db.query(models.Activity).filter(
                            models.Activity.activity_id == activity_id
                        ).first()
                        
                        if debug_steps:
                            debug_steps.append({
                                "step": 2,
                                "name": "Activity from Lookup",
                                "status": "success",
                                "description": f"Using activity from lookup: {found.get('activity_name')} ({found.get('lookup_criteria')})"
                            })
                        
                        if activity:
                            # Continue to analysis with this activity
                            return self._process_activity_for_analysis(
                                activity, request, debug_info, debug_steps, entities
                            )
                        break
            
            # Fallback if not found in previous results
            if debug_steps:
                debug_steps.append({
                    "step": 2,
                    "name": "Activity from Lookup",
                    "status": "fallback",
                    "description": "No found_activity in previous results, using last activity"
                })
        
        # Determine which activity to fetch based on activity_ref
        activity_ref = entities.get('activity_ref', 'last')
        
        # Get activity based on reference
        activity = None
        if activity_ref in ['today', 'yesterday']:
            target_date = self._resolve_date_from_entities({'date': activity_ref})
            activity = self._get_activity_by_date(request.user_id, target_date)
        elif activity_ref == 'previous':
            # Get the second most recent activity using direct DB query
            import models
            activities = self.db.query(models.Activity).filter(
                models.Activity.user_id == request.user_id
            ).order_by(models.Activity.start_time_local.desc()).limit(2).all()
            if len(activities) >= 2:
                activity = activities[1]  # Second most recent
            elif len(activities) == 1:
                activity = activities[0]
        else:  # 'last' or default
            activity = self.retriever.get_last_activity(request.user_id)
        
        if debug_steps:
            debug_steps.append({
                "step": 2,
                "name": "Date Resolution",
                "status": "success",
                "description": f"Activity ref: {activity_ref}" + (f" → {activity.activity_name}" if activity else " → Not found")
            })
        
        if not activity:
            return ChatResponse(
                message=f"'{activity_ref}' için aktivite bulunamadı.",
                debug_metadata=debug_info
            )
        
        # Process activity for analysis (common path)
        return self._process_activity_for_analysis(activity, request, debug_info, debug_steps, entities)
    
    def _process_activity_for_analysis(self, activity, request, debug_info, debug_steps, entities):
        """
        Common activity analysis processing - used by both regular activity_ref path
        and use_previous_activity path (from lookup).
        """
        # Get activity ID (handles both Activity model and ActivityCandidate)
        act_id = getattr(activity, 'garmin_activity_id', None) or getattr(activity, 'activity_id', None)
        act_date = getattr(activity, 'local_start_date', None)
        act_name = getattr(activity, 'activity_name', 'Unknown')
        
        # Fetch pack with full data
        pack = self._fetch_pack_from_db(request.user_id, act_id)
        
        # Build raw_data structure for handler chaining
        raw_data = self._build_raw_data_from_activity(activity, pack, request.user_id)
        
        # Store in debug_info for _execute_single_handler_with_data to pick up
        if debug_info is not None:
            debug_info['last_handler_data'] = raw_data
        
        # Pin this activity
        self.state_manager.pin_activity(
            request.user_id, 
            act_id, 
            act_date,
            act_name, 
            'training_detail'
        )
        
        return self._generate_activity_analysis(
            request, pack, act_name, debug_info, 
            act_id, act_date
        )
    
    def _build_raw_data_from_activity(self, activity, pack, user_id: int) -> Dict:
        """Build structured raw_data dict from activity and pack for handler chaining."""
        from datetime import date as date_type
        
        # Handle both Activity model and ActivityCandidate dataclass
        act_id = getattr(activity, 'garmin_activity_id', None) or getattr(activity, 'activity_id', None)
        act_name = getattr(activity, 'activity_name', 'Unknown')
        act_date = getattr(activity, 'local_start_date', None)
        
        # Get distance - Activity model has 'distance' in meters, ActivityCandidate has 'distance_km'
        if hasattr(activity, 'distance_km'):
            distance_km = activity.distance_km
        elif hasattr(activity, 'distance') and activity.distance:
            distance_km = activity.distance / 1000
        else:
            distance_km = None
        
        raw_data = {
            'activity': {
                'id': act_id,
                'name': act_name,
                'date': str(act_date) if act_date else '',
                'distance_km': distance_km,
            }
        }
        
        # Add pack data if available
        if pack:
            if hasattr(pack, 'avg_pace_str'):
                raw_data['activity']['avg_pace'] = pack.avg_pace_str
            if hasattr(pack, 'avg_hr') and pack.avg_hr:
                raw_data['activity']['avg_hr'] = pack.avg_hr
            if hasattr(pack, 'elevation_gain') and pack.elevation_gain:
                raw_data['activity']['elevation_gain'] = pack.elevation_gain
            if hasattr(pack, 'duration') and pack.duration:
                raw_data['activity']['duration'] = str(pack.duration)
            
            # Lap data with full details
            if hasattr(pack, 'laps') and pack.laps:
                raw_data['laps'] = []
                for lap in pack.laps[:10]:
                    lap_data = {
                        'distance_km': f"{lap.get('distance', 0)/1000:.2f}",
                        'pace': lap.get('pace_str', '?'),
                    }
                    if lap.get('avg_hr'):
                        lap_data['avg_hr'] = lap.get('avg_hr')
                    if lap.get('avg_power'):
                        lap_data['avg_power'] = lap.get('avg_power')
                    if lap.get('cadence'):
                        lap_data['cadence'] = lap.get('cadence')
                    raw_data['laps'].append(lap_data)
            
            # Add pack tables (laps, running dynamics)
            if hasattr(pack, 'tables') and pack.tables:
                raw_data['tables'] = pack.tables
            elif pack.get('tables'):
                raw_data['tables'] = pack.get('tables')
            
            # Add pack facts
            if hasattr(pack, 'facts') and pack.facts:
                raw_data['facts'] = pack.facts
            elif pack.get('facts'):
                raw_data['facts'] = pack.get('facts')
            
            # Weather data
            if pack.get('weather') or (hasattr(pack, 'weather') and pack.weather):
                raw_data['weather'] = pack.get('weather') or pack.weather
        
        # Get health data for this date
        activity_date = activity.local_start_date
        health_data = self._get_health_data_for_date(user_id, activity_date)
        if health_data:
            raw_data['health'] = health_data
        
        # Get training load
        training_load = self._get_training_load_for_user(user_id)
        if training_load:
            raw_data['training_load'] = training_load
        
        # Build full context string for LLM (same as _build_activity_context uses)
        # This is the complete formatted text that goes to the LLM
        act_id = getattr(activity, 'garmin_activity_id', None) or getattr(activity, 'activity_id', None)
        full_context = self._build_activity_context(
            pack, 
            act_name, 
            activity_date, 
            activity_id=act_id,
            user_id=user_id
        )
        raw_data['full_context_string'] = full_context
        
        return raw_data
    
    def _get_health_data_for_date(self, user_id: int, activity_date) -> Optional[Dict]:
        """Get HRV, sleep, stress data for a specific date."""
        try:
            from datetime import date as date_type, timedelta
            import models
            
            health = {}
            
            # HRV
            hrv = self.db.query(models.HRVLog).filter(
                models.HRVLog.user_id == user_id,
                models.HRVLog.calendar_date == activity_date
            ).first()
            if hrv and hrv.last_night_avg:
                health['hrv'] = hrv.last_night_avg
            
            # Sleep
            sleep = self.db.query(models.SleepLog).filter(
                models.SleepLog.user_id == user_id,
                models.SleepLog.calendar_date == activity_date
            ).first()
            if sleep:
                if sleep.sleep_score:
                    health['sleep_score'] = sleep.sleep_score
                if sleep.duration_seconds:
                    hours = sleep.duration_seconds // 3600
                    mins = (sleep.duration_seconds % 3600) // 60
                    health['sleep_duration'] = f"{hours}h {mins}m"
            
            # Stress  
            stress = self.db.query(models.StressLog).filter(
                models.StressLog.user_id == user_id,
                models.StressLog.calendar_date == activity_date
            ).first()
            if stress and stress.avg_stress:
                health['stress'] = stress.avg_stress
            
            return health if health else None
        except Exception as e:
            logging.warning(f"Failed to get health data: {e}")
            return None
    
    def _get_training_load_for_user(self, user_id: int) -> Optional[Dict]:
        """Get current CTL/ATL/TSB for user."""
        try:
            import models
            phys = self.db.query(models.PhysiologicalLog).filter(
                models.PhysiologicalLog.user_id == user_id
            ).order_by(models.PhysiologicalLog.calendar_date.desc()).first()
            
            if phys:
                return {
                    'ctl': phys.ctl if hasattr(phys, 'ctl') else None,
                    'atl': phys.atl if hasattr(phys, 'atl') else None,
                    'tsb': phys.tsb if hasattr(phys, 'tsb') else None,
                }
        except Exception as e:
            logging.warning(f"Failed to get training load: {e}")
        return None
    
    def _get_activity_by_date(self, user_id: int, target_date):
        """Get activity for a specific date."""
        import models
        from datetime import datetime
        
        activity = self.db.query(models.Activity).filter(
            models.Activity.user_id == user_id,
            models.Activity.start_time_local >= datetime.combine(target_date, datetime.min.time()),
            models.Activity.start_time_local < datetime.combine(target_date, datetime.max.time())
        ).order_by(models.Activity.start_time_local.desc()).first()
        
        return activity
    
    def _resolve_date_from_entities(self, entities: Dict[str, Any]):
        """Resolve a target date from extracted entities."""
        from datetime import date, timedelta
        
        date_ref = entities.get('date', '')
        
        if not date_ref:
            return None
        
        today = date.today()
        
        # Handle relative dates
        if date_ref == 'yesterday':
            return today - timedelta(days=1)
        elif date_ref == 'today':
            return today
        elif date_ref == 'last_week':
            return today - timedelta(days=7)
        elif date_ref == 'last_month':
            return today - timedelta(days=30)
        
        # Handle day names (Tuesday, etc.)
        day_names = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'pazartesi': 0, 'salı': 1, 'çarşamba': 2, 'perşembe': 3,
            'cuma': 4, 'cumartesi': 5, 'pazar': 6
        }
        
        if date_ref.lower() in day_names:
            target_weekday = day_names[date_ref.lower()]
            current_weekday = today.weekday()
            days_back = (current_weekday - target_weekday) % 7
            if days_back == 0:
                days_back = 7  # Last week's same day
            return today - timedelta(days=days_back)
        
        return None


    def _route_intent(self, request, parsed_intent, pinned_state, debug_info):
        """Route parsed intent to appropriate handler."""
        
        # PRIORITY 1: Greeting - always respond with simple greeting
        if parsed_intent.intent_type == 'greeting':
            if debug_info is not None:
                debug_info['handler_used'] = 'greeting'
            return ChatResponse(
                message=self.GREETING_RESPONSE, 
                debug_metadata=debug_info,
                debug_steps=[{"step": 1, "name": "Intent Detection", "status": "greeting", "description": "Selamlama algılandı, basit cevap döndürülüyor"}]
            )
        
        # PRIORITY 1.5: Farewell - simple goodbye
        if parsed_intent.intent_type == 'farewell':
            if debug_info is not None:
                debug_info['handler_used'] = 'farewell'
            return ChatResponse(
                message=self.FAREWELL_RESPONSE, 
                debug_metadata=debug_info,
                debug_steps=[{"step": 1, "name": "Intent Detection", "status": "farewell", "description": "Veda algılandı, basit cevap döndürülüyor"}]
            )
        
        # PRIORITY 2: General/SQL Agent queries - ignore activity context for these
        if parsed_intent.intent_type == 'general':
            if debug_info is not None:
                debug_info['handler_used'] = 'sql_agent'
            return self._handle_general_query(request, debug_info)
        
        # Case A: Explicit Activity ID provided (Frontend Context) - only for activity-specific intents
        if request.garmin_activity_id:
            if debug_info is not None:
                debug_info['handler_used'] = 'specific_activity'
                debug_info['reason'] = f'garmin_activity_id={request.garmin_activity_id} provided'
            return self._handle_specific_activity(request, request.garmin_activity_id, parsed_intent, debug_info)

        # Case B: Date Query -> Resolve & Pin
        if parsed_intent.intent_type == 'specific_date':
            if debug_info is not None:
                debug_info['handler_used'] = 'date_query'
            return self._handle_date_query(request, parsed_intent, debug_info)
        
        # Case C: Trend/Status Query
        if parsed_intent.intent_type == 'trend':
            if debug_info is not None:
                debug_info['handler_used'] = 'trend_query'
            return self._handle_trend_query(request, parsed_intent, debug_info)
        
        # Case C2: Race Strategy
        if parsed_intent.intent_type in ['race_strategy', 'workout_plan']:
            if debug_info is not None:
                debug_info['handler_used'] = 'race_strategy'
            return self._handle_race_strategy(request, parsed_intent, debug_info)
        
        # Case C3: Temporal Query ("neden şubat'ta formsuzdum?")
        if parsed_intent.intent_type == 'temporal_query':
            if debug_info is not None:
                debug_info['handler_used'] = 'temporal_query'
            return self._handle_temporal_query(request, parsed_intent, debug_info)
        
        # Case C4: Progression Query ("VO2max nasıl gelişti?")
        if parsed_intent.intent_type == 'progression_query':
            if debug_info is not None:
                debug_info['handler_used'] = 'progression_query'
            return self._handle_progression_query(request, parsed_intent, debug_info)
        
        # Case D: Longitudinal (uses pinned date/load)
        if parsed_intent.intent_type == 'longitudinal_prep':
            if debug_info is not None:
                debug_info['handler_used'] = 'longitudinal_prep'
            return self._handle_longitudinal_query(request, parsed_intent, pinned_state, debug_info)
        
        # Case E: Health (uses pinned date)
        if parsed_intent.intent_type == 'health_day_status':
            if debug_info is not None:
                debug_info['handler_used'] = 'health_query'
            return self._handle_health_query(request, parsed_intent, pinned_state, debug_info)
            
        # Case F: Follow-up Analysis (laps, technique, general) -> Needs Context
        if parsed_intent.intent_type in ['activity_analysis', 'laps_or_splits', 'technique']:
            if debug_info is not None:
                debug_info['handler_used'] = 'activity_followup'
            return self._handle_activity_followup(request, parsed_intent, pinned_state, debug_info)

        # Case G: Last Activity
        if parsed_intent.intent_type == 'last_activity':
            if debug_info is not None:
                debug_info['handler_used'] = 'last_activity'
            return self._handle_last_activity(request, parsed_intent, debug_info)

        # Case H: Specific Activity Name (e.g., "Almada koşusu")
        if parsed_intent.intent_type == 'specific_name':
            if debug_info is not None:
                debug_info['handler_used'] = 'specific_name'
            return self._handle_name_query(request, parsed_intent, debug_info)

        # FALLBACK: Unknown intent -> SQL Agent
        if debug_info is not None:
            debug_info['handler_used'] = 'sql_agent_fallback'
        return self._handle_general_query(request, debug_info)
    
    # ==========================================================================
    # HANDLERS
    # ==========================================================================
    
    def _handle_greeting(self, request, debug_info):
        """Simple, warm greeting without any data fabrication."""
        return ChatResponse(message=self.GREETING_RESPONSE, debug_metadata=debug_info)

    def _handle_specific_activity(self, request, activity_id, intent, debug_info):
        """Analyze a specific activity with full context."""
        if request.activity_details_json:
            pack = self.pack_builder.build_pack(request.activity_details_json)
            local_date = request.activity_details_json.get('local_start_date') or date.today()
            if isinstance(local_date, str):
                 try: local_date = datetime.strptime(local_date[:10], "%Y-%m-%d").date()
                 except: pass
            
            self.state_manager.pin_activity(
                request.user_id, activity_id, local_date, 
                request.activity_details_json.get('activityName', 'Koşu'), 
                'specific_activity'
            )
            activity_name = request.activity_details_json.get('activityName', 'Koşu')
        else:
            pack = self._fetch_pack_from_db(request.user_id, activity_id)
            if not pack:
                 return ChatResponse(message="Bu aktivite için detay verisi bulamadım. Garmin'den senkronize olmuş mu?", debug_metadata=debug_info)
            activity_name = "Koşu"
            local_date = date.today()
            
        return self._generate_activity_analysis(request, pack, activity_name, debug_info, activity_id, local_date)

    def _handle_date_query(self, request, intent, debug_info):
        """Find and analyze activity from a specific date."""
        target_date = intent.mentioned_dates[0]
        candidates = self.retriever.get_candidates_by_date(request.user_id, target_date)
        resolution = self.retriever.resolve_candidates(candidates, None)
        
        if resolution.status == 'selected':
            activity = resolution.selected
            self.state_manager.pin_activity(
                request.user_id, activity.garmin_activity_id, activity.local_start_date,
                activity.activity_name, 'specific_date'
            )
            pack = self._fetch_pack_from_db(request.user_id, activity.garmin_activity_id)
            return self._generate_activity_analysis(request, pack, activity.activity_name, debug_info, activity.garmin_activity_id, activity.local_start_date)
        
        if resolution.status == 'needs_clarification':
            return ChatResponse(message=resolution.clarification_message, debug_metadata=debug_info)
            
        return ChatResponse(
            message=f"{target_date.strftime('%d %B')} tarihinde kayıtlı koşu bulamadım. Başka bir tarih deneyelim mi?", 
            debug_metadata=debug_info
        )

    def _handle_trend_query(self, request, intent, debug_info):
        """Analyze recent training trend/form."""
        # Check for environmental queries - these need SmartQueryEngine
        env_keywords = ['sıcak', 'soğuk', 'yağmur', 'rüzgar', 'rakım', 'irtifa', 'hava', 'nem', 'kış', 'yaz']
        if any(kw in request.message.lower() for kw in env_keywords):
            return self._handle_general_query(request, debug_info)
        
        anchor_date = date.today()
        
        # Use get_current_load for reading (doesn't recalculate)
        stats = self.load_engine.get_current_load(request.user_id, anchor_date)
        
        # Also get today's health data for context
        health_data = self.load_engine.get_health_data(request.user_id, anchor_date)
        
        # Get recent activity count
        recent_activities = self.repo.get_activity_summaries_range(
            request.user_id, 
            anchor_date - timedelta(days=7), 
            anchor_date
        )
        
        context = self._build_trend_context(stats, len(recent_activities), anchor_date, health_data)
        return self._generate_conversational_response(request, context, "trend", debug_info)

    def _handle_race_strategy(self, request, intent, debug_info):
        """Analyze past performances and generate personalized race strategy."""
        # Get full performance profile with PRs, VDOT, predictions
        profile = self.performance_analyzer.get_performance_profile(request.user_id)
        
        # Get current form
        stats = self.load_engine.get_current_load(request.user_id)
        
        # Format profile for prompt
        profile_text = self.performance_analyzer.format_profile_for_prompt(profile)
        
        # Build context
        context_lines = [profile_text]
        
        # Add current form
        context_lines.append(f"\n## MEVCUT FORM")
        context_lines.append(f"- Fitness (CTL): {stats['ctl']:.1f}")
        context_lines.append(f"- Form (TSB): {stats['tsb']:.1f}")
        context_lines.append(f"- Durum: {stats.get('form_status', 'UNKNOWN')}")
        
        context_lines.append(f"\n## KULLANICI SORUSU\n{request.message}")
        
        context = "\n".join(context_lines)
        
        # Generate personalized strategy
        prompt = f"""{self.COACH_PERSONA}

{self.RUNNING_EXPERTISE}

# VERİ
{context}

# TALİMAT
Kullanıcının GERÇEK performans profilini kullanarak yarış stratejisi oluştur:

1. **PR'larına bak** - En iyi süreleri ne? Ne zaman koşulmuş?
2. **VDOT'unu kullan** - Bu, gerçek aerobik kapasitesini gösterir
3. **Tahminleri referans al** - Riegel formülüyle hesaplanmış gerçek tahminler var
4. **Güçlü/zayıf yönleri değerlendir**

SPESİFİK PACE HEDEF VER:
- İlk km: X:XX/km
- Orta (2-8 km): X:XX/km  
- Son 2km: X:XX/km

Geçmişteki yarışlardan ÖRNEK VER. Trend'i (gelişiyor mu?) değerlendir.
200-250 kelime.
"""
        
        resp = self.llm.generate(prompt, max_tokens=700)
        return ChatResponse(message=resp.text, debug_metadata=debug_info)

    def _handle_temporal_query(self, request, intent, debug_info):
        """Handle temporal/historical queries like 'neden şubat'ta formsuzdum?'"""
        # Get full athlete memory
        memory = self.memory_store.get_memory(request.user_id)
        
        # Build rich context with all temporal layers
        context = memory.get_full_context(max_chars=4000)
        
        prompt = f"""{self.COACH_PERSONA}

{self.RUNNING_EXPERTISE}

# ATLETİN TÜM GEÇMİŞİ
{context}

# KULLANICI SORUSU
{request.message}

# TALİMAT
Bu bir TEMPORAL soru - kullanıcı geçmişle ilgili bir şey soruyor.
- Geçmiş verilerine dayalı cevap ver
- Tarihlere, dönemlere, olaylara referans ver
- Değişimlerin NEDEN olduğunu açıkla (uyku, stres, antrenman yükü)
- Karşılaştırma yaparken net rakamlar kullan
- 200-300 kelime
"""
        
        resp = self.llm.generate(prompt, max_tokens=700)
        return ChatResponse(message=resp.text, debug_metadata=debug_info)

    def _handle_progression_query(self, request, intent, debug_info):
        """Handle progression queries like 'VO2max nasıl değişti?'"""
        # Get full athlete memory
        memory = self.memory_store.get_memory(request.user_id)
        
        # Focus on fitness trajectory
        trajectory = memory.fitness_trajectory
        career = memory.career
        
        # Build progression-focused context
        context_lines = ["# FITNESS GELİŞİM ANALİZİ"]
        
        # VO2max trend
        context_lines.append(f"\n## VO2MAX TRENDİ")
        context_lines.append(trajectory.trend_description())
        if trajectory.vo2max_peak:
            d, v = trajectory.vo2max_peak
            context_lines.append(f"- En yüksek: {v} ({d})")
        if trajectory.vo2max_low:
            d, v = trajectory.vo2max_low
            context_lines.append(f"- En düşük: {v} ({d})")
        
        # PRs
        context_lines.append(f"\n## EN İYİ SÜRELER")
        for label, pr in career.personal_records.items():
            days_ago = (date.today() - pr.date).days
            freshness = "taze" if days_ago < 90 else "eski"
            context_lines.append(f"- {label}: {pr.time_str()} ({pr.pace_per_km}/km) - {days_ago} gün önce ({freshness})")
        
        # Seasonal comparison
        if len(memory.seasons) >= 2:
            context_lines.append(f"\n## SEZON KARŞILAŞTIRMASI")
            for s in memory.seasons[:3]:
                context_lines.append(f"- {s.period_name}: {s.total_km:.0f}km, VO2max {s.vo2max_start}→{s.vo2max_end}")
        
        # Patterns
        context_lines.append(f"\n## ANTRENMAN PATERNLERİ")
        for pat in memory.patterns[:3]:
            context_lines.append(f"- {pat.description}")
        
        context = "\n".join(context_lines)
        
        prompt = f"""{self.COACH_PERSONA}

{self.RUNNING_EXPERTISE}

{context}

# KULLANICI SORUSU
{request.message}

# TALİMAT
Bu bir PROGRESSION (gelişim) sorusu.
- Zaman içindeki değişimi net göster (rakamlarla)
- VO2max, pace, hacim değişimlerini karşılaştır
- Gelişimin nedenlerini açıkla
- Gelecek için tahmin/öneri yap
- Eğer düşüş varsa nedenini belirt (uyku, stres, tutarsızlık)
- 200-300 kelime
"""
        
        resp = self.llm.generate(prompt, max_tokens=700)
        return ChatResponse(message=resp.text, debug_metadata=debug_info)

    def _handle_longitudinal_query(self, request, intent, pinned_state, debug_info):
        """Analyze preparation period leading to a race/goal."""
        anchor_date = intent.anchor_date or (pinned_state.local_start_date if pinned_state.is_valid else date.today())
        days = intent.trend_days or 90
        
        stats = self.load_engine.calculate_sync_load(request.user_id, anchor_date)
        context = f"""
HAZIRLIK ANALİZİ (Son {days} gün, bitiş: {anchor_date}):
- Fitness (CTL): {stats['ctl']:.1f}
- Yorgunluk (ATL): {stats['atl']:.1f}  
- Form (TSB): {stats['tsb']:.1f}

TSB YORUMU:
- Pozitif TSB = dinlenmiş, yarışa hazır
- -10 ile -30 arası = antrenman yükü altında (normal)
- -30'un altı = aşırı yüklenme riski
"""
        return self._generate_conversational_response(request, context, "longitudinal", debug_info, date_val=anchor_date)
        
    def _handle_activity_followup(self, request, intent, pinned_state, debug_info):
        """Handle follow-up questions about current activity."""
        if not pinned_state.is_valid:
            return ChatResponse(
                message="Hangi aktiviteden bahsettiğimizi unuttum. 'Son koşumu analiz et' ya da tarih söyleyebilir misin?", 
                debug_metadata=debug_info
            )
        
        self.state_manager.extend_expiry(request.user_id)
        
        if request.activity_details_json:
            pack = self.pack_builder.build_pack(request.activity_details_json)
        else:
            pack = self._fetch_pack_from_db(request.user_id, pinned_state.garmin_activity_id)
            
        if not pack:
            return ChatResponse(message="Aktivite verisine ulaşamıyorum. Tekrar senkronize etmeyi deneyelim mi?", debug_metadata=debug_info)
             
        return self._generate_activity_analysis(request, pack, pinned_state.activity_name or "Koşu", debug_info, pinned_state.garmin_activity_id, pinned_state.local_start_date)

    def _handle_health_query(self, request, intent, pinned_state, debug_info):
        """Handle questions about sleep, recovery, readiness."""
        target_date = intent.anchor_date or (pinned_state.local_start_date if pinned_state.is_valid else date.today())
        
        # Fetch actual health data from database
        health_data = self.load_engine.get_health_data(request.user_id, target_date)
        
        if health_data:
            context_lines = [f"SAĞLIK VERİSİ ({target_date}):"]
            
            if health_data.get('sleep'):
                s = health_data['sleep']
                context_lines.append(f"- Uyku Skoru: {s.get('score', 'N/A')}/100")
                context_lines.append(f"- Süre: {s.get('duration_hrs', 0)} saat")
                context_lines.append(f"- Derin Uyku: {s.get('deep_pct', 0)}%")
                context_lines.append(f"- REM: {s.get('rem_pct', 0)}%")
            
            if health_data.get('hrv'):
                h = health_data['hrv']
                context_lines.append(f"- HRV: {h.get('value', 'N/A')} ms ({h.get('status', '')})")
                if h.get('baseline_low') and h.get('baseline_high'):
                    context_lines.append(f"- HRV Baseline: {h['baseline_low']}-{h['baseline_high']} ms")
            
            if health_data.get('stress'):
                st = health_data['stress']
                context_lines.append(f"- Stres: Ort {st.get('avg', 'N/A')}, Max {st.get('max', 'N/A')} ({st.get('status', '')})")
            
            context = "\n".join(context_lines)
        else:
            context = f"Bu tarih ({target_date}) için sağlık verisi bulunamadı. Garmin Connect'ten senkronize edilmiş mi?"
             
        return self._generate_conversational_response(request, context, "health", debug_info, date_val=target_date)

    def _handle_last_activity(self, request, intent, debug_info):
        """Fetch and analyze the most recent activity."""
        activity = self.retriever.get_last_activity(request.user_id)
        if not activity:
            return ChatResponse(message="Henüz kayıtlı koşu yok. İlk koşunu yaptıktan sonra analiz yapalım! 🏃", debug_metadata=debug_info)
        
        self.state_manager.pin_activity(request.user_id, activity.garmin_activity_id, activity.local_start_date, activity.activity_name, 'last_activity')
        pack = self._fetch_pack_from_db(request.user_id, activity.garmin_activity_id)
        
        return self._generate_activity_analysis(request, pack, activity.activity_name, debug_info, activity.garmin_activity_id, activity.local_start_date)

    def _handle_name_query(self, request, intent, debug_info):
        """Find activities by name (e.g., 'Almada koşusu')."""
        keywords = intent.activity_name_keywords
        if not keywords:
            return ChatResponse(message=self.NO_DATA_RESPONSE, debug_metadata=debug_info)
        
        # Search for matching activities
        all_candidates = []
        for keyword in keywords:
            candidates = self.retriever.get_candidates_by_name(request.user_id, keyword, date_window_days=365)
            all_candidates.extend(candidates)
        
        # Remove duplicates by activity ID
        seen = set()
        unique_candidates = []
        for c in all_candidates:
            if c.garmin_activity_id not in seen:
                seen.add(c.garmin_activity_id)
                unique_candidates.append(c)
        
        if not unique_candidates:
            return ChatResponse(
                message=f"'{keywords[0]}' ile eşleşen aktivite bulamadım. Tarih belirtebilir misin? (örn: '15 Kasım'taki koşu')",
                debug_metadata=debug_info
            )
        
        # Single match - analyze it
        if len(unique_candidates) == 1:
            activity = unique_candidates[0]
            self.state_manager.pin_activity(
                request.user_id, activity.garmin_activity_id, activity.local_start_date,
                activity.activity_name, 'specific_name'
            )
            pack = self._fetch_pack_from_db(request.user_id, activity.garmin_activity_id)
            return self._generate_activity_analysis(request, pack, activity.activity_name, debug_info, activity.garmin_activity_id, activity.local_start_date)
        
        # Multiple matches - ask for clarification with suggestions
        suggestions = []
        for c in unique_candidates[:5]:  # Max 5 suggestions
            date_str = c.local_start_date.strftime("%d %B")
            suggestions.append(f"• **{c.activity_name}** ({date_str}) - {c.distance_km:.1f} km")
        
        suggestion_list = "\n".join(suggestions)
        return ChatResponse(
            message=f"'{keywords[0]}' ile {len(unique_candidates)} aktivite buldum:\n\n{suggestion_list}\n\nHangisini analiz edeyim? Tarihi söyleyebilirsin.",
            debug_metadata=debug_info
        )

    def _handle_general_query(self, request, debug_info, incoming_debug_steps=None, entities: Dict[str, Any] = None):
        """
        Handle general questions with SQL Agent.
        
        Two modes based on entities:
        1. LOOKUP: Find specific activity by criteria (entities.query_type == "lookup")
           - Returns found_activity with activity_id for chaining to training_detail_handler
        2. AGGREGATE: Calculate stats (default mode)
           - Returns aggregate statistics
        """
        if entities is None:
            entities = {}
        
        # LOOKUP MODE: Find specific activity by criteria
        if entities.get('query_type') == 'lookup':
            return self._handle_lookup_query(request, debug_info, incoming_debug_steps, entities)
        
        # AGGREGATE MODE (default): Use SQL Agent for stats
        # Enhance the question with entity context for SQL Agent
        enhanced_question = self._enhance_question_with_entities(request.message, entities)
        
        try:
            response_text, sql_debug = self.sql_agent.analyze_and_answer(
                request.user_id, 
                enhanced_question
            )
            
            # Merge incoming debug_steps (AI Intent) with SQL Agent steps
            sql_steps = sql_debug.get("steps", [])
            if incoming_debug_steps:
                debug_steps = incoming_debug_steps + sql_steps
            else:
                debug_steps = sql_steps
            
            if debug_info is not None:
                debug_info['sql_agent'] = sql_debug
                debug_info['enhanced_question'] = enhanced_question
            
            return ChatResponse(
                message=response_text, 
                debug_metadata=debug_info,
                debug_steps=debug_steps
            )
        except Exception as e:
            logging.error(f"SQLAgent failed: {e}")
            return ChatResponse(message=self.NO_DATA_RESPONSE, debug_metadata=debug_info)
    
    def _handle_lookup_query(self, request, debug_info, incoming_debug_steps, entities: Dict[str, Any]):
        """
        Handle lookup queries: Find specific activity by criteria using SQL Agent dynamically.
        
        Instead of hardcoded criteria, uses SQL Agent to generate the appropriate query
        based on the description. This supports any metric (elevation_gain, avg_hr, etc.)
        
        Returns found_activity in raw_data for training_detail_handler to use.
        """
        import models
        from sqlalchemy import text
        
        description = entities.get('description', '')
        lookup_criteria = entities.get('lookup_criteria', 'custom')
        
        debug_steps = incoming_debug_steps or []
        
        # Build a lookup prompt for SQL Agent
        # Ask it to find the activity_id of the activity matching the criteria
        lookup_prompt = f"""
DATABASE: PostgreSQL (strftime() KULLANMA! DATE_TRUNC, EXTRACT, TO_CHAR kullan)

TABLOLAR:
1. activities - Aktivite verileri
   - activity_id, activity_name, local_start_date, start_time_local
   - elevation_gain, distance, average_hr, max_hr, avg_speed, training_effect, weather_temp
   - user_id, activity_type

2. hrv_logs - HRV verileri (aktivite günü ile JOIN et)
   - calendar_date, last_night_avg (HRV değeri), weekly_avg
   - user_id

3. sleep_logs - Uyku verileri (aktivite günü ile JOIN et)
   - calendar_date, sleep_score, sleep_time_seconds
   - user_id

Kullanıcı şunu soruyor: "{description}"

GÖREV: Bu kritere uyan TEK BİR aktivitenin activity_id'sini bul.

KURALLAR:
1. SELECT activity_id, activity_name, local_start_date ve ilgili metriği seç
2. activities tablosundan sorgula (HRV/uyku için JOIN yap)
3. user_id = :user_id filtresini MUTLAKA ekle
4. activity_type = 'running' filtresini ekle
5. İlgili metriğin NULL olmadığından emin ol
6. Doğru ORDER BY kullan (DESC veya ASC)
7. LIMIT 5 kullan

ÖRNEKLER:
- "En yüksek elevation gain": ORDER BY elevation_gain DESC
- "En düşük HRV ile çıktığım antrenman":
  SELECT a.activity_id, a.activity_name, a.local_start_date, h.last_night_avg
  FROM activities a
  JOIN hrv_logs h ON a.local_start_date = h.calendar_date AND a.user_id = h.user_id
  WHERE a.user_id = :user_id AND a.activity_type = 'running' AND h.last_night_avg IS NOT NULL
  ORDER BY h.last_night_avg ASC LIMIT 5

- "En kötü uyku sonrası koşu":
  SELECT a.activity_id, a.activity_name, a.local_start_date, s.sleep_score
  FROM activities a
  JOIN sleep_logs s ON a.local_start_date = s.calendar_date AND a.user_id = s.user_id
  WHERE a.user_id = :user_id AND a.activity_type = 'running' AND s.sleep_score IS NOT NULL
  ORDER BY s.sleep_score ASC LIMIT 5

SQL:
"""
        
        try:
            # Use SQL Agent's LLM to generate the query
            sql_response = self.llm.generate(lookup_prompt, max_tokens=400)
            sql_text = sql_response.text.strip()
            
            # Extract SQL from response
            if "```sql" in sql_text:
                sql_text = sql_text.split("```sql")[1].split("```")[0].strip()
            elif "```" in sql_text:
                sql_text = sql_text.split("```")[1].split("```")[0].strip()
            
            # Ensure it's a SELECT query
            if not sql_text.upper().startswith("SELECT"):
                raise ValueError(f"Invalid SQL generated: {sql_text[:100]}")
            
            debug_steps.append({
                "step": 1,
                "name": "Lookup Query Generation",
                "status": "success",
                "description": f"SQL Agent generated query for: {description}",
                "sql": sql_text,
                "prompt_sent": lookup_prompt[:500] + "..." if len(lookup_prompt) > 500 else lookup_prompt
            })
            
            # Execute the query
            result = self.db.execute(
                text(sql_text),
                {"user_id": request.user_id}
            )
            rows = result.fetchall()
            columns = result.keys()
            
            if not rows:
                debug_steps.append({
                    "step": 2,
                    "name": "Lookup Query",
                    "status": "not_found",
                    "description": f"No activity found for: {description}",
                    "sql": sql_text
                })
                return ChatResponse(
                    message=f"'{description}' kriterine göre aktivite bulunamadı.",
                    debug_metadata=debug_info,
                    debug_steps=debug_steps
                )
            
            # Format sample results for debug
            sample_results = []
            for row in rows[:5]:
                row_dict = dict(zip(columns, row))
                sample_results.append({
                    'activity_name': row_dict.get('activity_name', 'Unknown'),
                    'date': str(row_dict.get('local_start_date', '')),
                    **{k: v for k, v in row_dict.items() if k not in ['activity_id', 'activity_name', 'local_start_date', 'user_id']}
                })
            
            # Get the first result
            first_row = dict(zip(columns, rows[0]))
            activity_id = first_row.get('activity_id')
            activity_name = first_row.get('activity_name', 'Unknown')
            activity_date = first_row.get('local_start_date', '')
            
            # Build found_activity for chaining
            found_activity = {
                'activity_id': activity_id,
                'activity_date': str(activity_date) if activity_date else None,
                'activity_name': activity_name,
                'lookup_criteria': lookup_criteria,
                'description': description,
                # Include all metrics from the query
                **{k: v for k, v in first_row.items() if k not in ['activity_id', 'user_id']}
            }
            
            debug_steps.append({
                "step": 2,
                "name": "Lookup Query",
                "status": "success",
                "description": f"Found: {activity_name} ({activity_date})",
                "found_activity": found_activity,
                "sql": sql_text,
                "result_count": len(rows),
                "sample_results": sample_results
            })
            
            # Store in debug_info for handler chaining
            if debug_info is not None:
                debug_info['last_handler_data'] = {'found_activity': found_activity}
            
            # Return brief message (training_detail_handler will provide analysis)
            response_msg = f"'{description}' kriterine göre {activity_name} ({activity_date}) bulundu."
            
            return ChatResponse(
                message=response_msg,
                debug_metadata=debug_info,
                debug_steps=debug_steps
            )
            
        except Exception as e:
            logging.error(f"Lookup query failed: {e}")
            debug_steps.append({
                "step": 1,
                "name": "Lookup Query",
                "status": "error",
                "description": str(e)
            })
            return ChatResponse(
                message=f"Aktivite aramasında hata: {str(e)[:100]}",
                debug_metadata=debug_info,
                debug_steps=debug_steps
            )
    
    def _enhance_question_with_entities(self, question: str, entities: Dict[str, Any]) -> str:
        """
        Enhance user question with extracted entity context.
        Helps SQL Agent generate more accurate queries.
        """
        enhancements = []
        
        if entities.get('metric'):
            metric_map = {
                'distance': 'mesafe (km)',
                'pace': 'pace (dk/km)',
                'hr': 'nabız (bpm)',
                'power': 'güç (watt)',
                'cadence': 'kadans (adım/dk)',
                'time': 'süre'
            }
            metric = entities['metric']
            enhancements.append(f"[Metrik: {metric_map.get(metric, metric)}]")
        
        if entities.get('date'):
            date_ref = entities['date']
            date_map = {
                'yesterday': 'dün',
                'today': 'bugün',
                'last_week': 'son 7 gün',
                'last_month': 'son 30 gün'
            }
            enhancements.append(f"[Tarih: {date_map.get(date_ref, date_ref)}]")
        
        if entities.get('comparison'):
            comp_map = {
                'weekly': 'haftalık karşılaştırma',
                'monthly': 'aylık karşılaştırma',
                'trend': 'trend analizi'
            }
            enhancements.append(f"[Karşılaştırma: {comp_map.get(entities['comparison'], entities['comparison'])}]")
        
        if enhancements:
            return f"{question} {' '.join(enhancements)}"
        return question

    # ==========================================================================
    # RESPONSE GENERATORS
    # ==========================================================================
    
    def _generate_activity_analysis(self, request, pack, activity_name, debug_info, act_id, date_val):
        """Generate a conversational activity analysis."""
        if not pack:
            return ChatResponse(message="Bu aktivite için veri bulamadım.", debug_metadata=debug_info)
        
        # Check if user wants detailed analysis
        wants_detail = any(w in request.message.lower() for w in ['detay', 'derin', 'kapsamlı', 'tam', 'her', 'tüm'])
        
        # Build rich context
        context = self._build_activity_context(pack, activity_name, date_val, activity_id=act_id, user_id=request.user_id)
        
        # Include conversation history for continuity
        history_context = self._format_conversation_history(request.conversation_history)
        
        # Get athlete memory brief for context
        try:
            memory = self.memory_store.get_memory(request.user_id)
            athlete_brief = memory.career.to_brief() if memory.career else ""
        except Exception:
            athlete_brief = ""
        
        if wants_detail:
            detail_instruction = """
- DETAYLI ANALİZ İSTENİYOR - ekstra derinlemesine bak:
  - Lap bazında performans değişimi
  - Nabız bölge dağılımı
  - Kadans ve stride length değerlendirmesi
  - Önceki koşularla karşılaştırma
  - Spesifik iyileştirme önerileri
- ANALİZİ DERİNLEŞTİR: Sporcunun performansını tüm detaylarıyla açıkla.
- FORMAT: Asla bold (**) veya italic (*) kullanma. Plain text cevap ver.
"""
        else:
            detail_instruction = """
- LAP TABLOSUNU ANALİZ ET VE ANTRENMAN TÜRÜNÜ KEŞFET:
  - Lap'leri incele, interval pattern'ı bul (örn: 8x30sn, 6x200m, 4x1km)
  - Kısa-hızlı lap'ler interval, uzun-yavaş lap'ler ısınma/soğuma
  - Interval'lerde pace, HR, power değişimini yorumla
  - Recovery lap'lerinde toparlanma kalitesini değerlendir
- Veriyi hikaye gibi anlat, tablo formatı kullanma.
- Önemli noktaları vurgula ama her detayı sayma.
- CTL/ATL/TSB verisi varsa form durumunu yorumla.
- Elevation verisi varsa değerlendir (tırmanış nabzı etkisi).
- Yüksek rakım koşusuysa (Kapadokya, Bolu vb) bunu belirt.
- FORMAT: HİÇBİR MARKDOWN SEMBOLÜ KULLANMA. Asla bold (**) veya italic (*) kullanma. Plain text cevap ver.
"""
        
        prompt = f"""# SENİ TANIYORUM
{athlete_brief}

# SOHBET GEÇMİŞİ
{history_context}

# AKTİVİTE VERİSİ
{context}

# SPORCU SORUSU
{request.message}

# TALİMAT
{detail_instruction}
"""
        
        max_tokens = 1500 if wants_detail else 1000
        resp = self.llm.generate(prompt, max_tokens=max_tokens)
        
        # Force clean markdown
        resp = LLMResponse(
            text=self._clean_markdown(resp.text),
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            model=resp.model
        )
        
        # Light validation - don't reject, just log
        is_valid, violation = self.evidence_gate.validate(resp.text, context + "\n" + request.message)
        if not is_valid:
            logging.warning(f"Potential hallucination: {violation}")
        
        # Build debug_steps for activity analysis
        debug_steps = [
            {
                "step": 1,
                "name": "Activity Data Loaded",
                "status": "success",
                "description": f"Aktivite: {activity_name}",
                "data_source": "activities table + analysis pack",
                "activity_context": context  # Full context, no truncation
            },
            {
                "step": 2,
                "name": "LLM Analysis",
                "status": "success",
                "prompt_sent": prompt,  # Full prompt, no truncation
                "llm_response": resp.text,  # Full response, no truncation
                "description": "LLM koşuyu analiz etti"
            }
        ]
            
        return ChatResponse(
            message=resp.text, 
            resolved_activity_id=act_id, 
            resolved_date=str(date_val) if date_val else None, 
            debug_metadata=debug_info,
            debug_steps=debug_steps
        )

    def _generate_conversational_response(self, request, context, context_type, debug_info, activity_id=None, date_val=None):
        """Generate a natural conversational response with athlete memory."""
        history_context = self._format_conversation_history(request.conversation_history)
        
        # Get athlete memory brief (cached, fast)
        try:
            memory = self.memory_store.get_memory(request.user_id)
            athlete_brief = memory.career.to_brief() if memory.career else ""
        except Exception:
            athlete_brief = ""
        
        prompt = f"""{self.COACH_PERSONA}

{self.RUNNING_EXPERTISE}

# SENİ TANIYORUM
{athlete_brief}

# SOHBET GEÇMİŞİ
{history_context}

# MEVCUT VERİ
{context}

# SPORCU SORUSU
{request.message}

# TALİMAT
- Doğal ve samimi konuş.
- Geçmiş performanslarına referans ver (PR'lar, VO2max trendi).
- Fazla teknik olmadan durumu özetle.
- Bir sonraki adım için öneri ver.
- 100-150 kelime civarı tut.
"""
        
        resp = self.llm.generate(prompt, max_tokens=400)
        
        # Build debug_steps for conversational response
        debug_steps = [
            {
                "step": 1,
                "name": f"Context Build ({context_type})",
                "status": "success",
                "description": f"{context_type} verisi yüklendi",
                "context_preview": context[:200] + "..." if len(context) > 200 else context
            },
            {
                "step": 2,
                "name": "LLM Response",
                "status": "success",
                "prompt_sent": prompt,  # Full prompt
                "llm_response": resp.text,  # Full response
                "description": "LLM cevap üretti"
            }
        ]
             
        return ChatResponse(
            message=resp.text, 
            resolved_activity_id=activity_id, 
            resolved_date=str(date_val) if date_val else None, 
            debug_metadata=debug_info,
            debug_steps=debug_steps
        )

    # ==========================================================================
    # CONTEXT BUILDERS
    # ==========================================================================
    
    def _build_activity_context(self, pack, activity_name, activity_date, activity_id=None, user_id: int = 1) -> str:
        """Build rich context from activity pack including real elevation, weather, and health data."""
        import models
        from sqlalchemy import func
        from datetime import date as date_type, datetime, timedelta
        
        # Calculate relative time
        today = date_type.today()
        relative_time = ""
        activity_date_obj = None
        
        if activity_date:
            if isinstance(activity_date, str):
                try:
                    activity_date_obj = datetime.strptime(activity_date.split('T')[0], '%Y-%m-%d').date()
                except:
                    activity_date_obj = None
            elif isinstance(activity_date, (date_type, datetime)):
                activity_date_obj = activity_date if isinstance(activity_date, date_type) else activity_date.date()
            
            if activity_date_obj:
                days_ago = (today - activity_date_obj).days
                if days_ago == 0:
                    relative_time = "bugün"
                elif days_ago == 1:
                    relative_time = "dün"
                elif days_ago <= 6:
                    relative_time = f"{days_ago} gün önce"
                elif days_ago <= 13:
                    relative_time = "geçen hafta"
                elif days_ago <= 30:
                    weeks = days_ago // 7
                    relative_time = f"{weeks} hafta önce"
                else:
                    months = days_ago // 30
                    relative_time = f"{months} ay önce"
        
        # Format date for display (Turkish)
        date_display = ""
        if activity_date_obj:
            months_tr = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 
                        'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
            date_display = f"{activity_date_obj.day} {months_tr[activity_date_obj.month]}"
        
        # Build activity link
        activity_link = ""
        if activity_id:
            activity_link = f"[{activity_name} ({date_display})](activity://{activity_id})"
        else:
            activity_link = f"{activity_name} ({date_display})"
        
        lines = [f"📅 BUGÜNÜN TARİHİ: {today.day} {months_tr[today.month]} {today.year}"]
        lines.append(f"\n🏃 AKTİVİTE: {activity_link}")
        lines.append(f"   activity_id: {activity_id}")
        if relative_time:
            lines.append(f"   Zaman: {relative_time}")
        if activity_date:
            lines.append(f"   Tarih: {activity_date}")
        
        if pack.get('facts'):
            facts = pack['facts']
            lines.append(f"\nTemel Metrikler:\n{facts}")
            
            # Extract elevation and weather for emphasis
            elev_line = [l for l in facts.split('\n') if 'ELEV_GAIN' in l]
            temp_line = [l for l in facts.split('\n') if 'WEATHER_TEMP' in l]
            
            if elev_line:
                lines.append(f"\n⛰️ İRTİFA ANALİZİ:")
                lines.append(f"- {elev_line[0]}")
                lines.append("- Yüksek tırmanış nabzı %5-15 artırır")
                lines.append("- Downhill iniş kasları yorar, kadansı düşürür")
            
            if temp_line:
                lines.append(f"\n🌡️ HAVA KOŞULLARI:")
                lines.append(f"- {temp_line[0]}")
                hum_line = [l for l in facts.split('\n') if 'HUMIDITY' in l]
                wind_line = [l for l in facts.split('\n') if 'WIND' in l]
                if hum_line:
                    lines.append(f"- {hum_line[0]}")
                if wind_line:
                    lines.append(f"- {wind_line[0]}")
                lines.append("- Sıcak hava nabzı artırır, performansı düşürür")
                lines.append("- Soğuk hava kasları sertleştirir")
        
        # REAL ALTITUDE FROM GPS DATA (not hardcoded!)
        if activity_id:
            try:
                altitude_stats = self.db.query(
                    func.min(models.ActivityStream.altitude).label('min_alt'),
                    func.max(models.ActivityStream.altitude).label('max_alt'),
                    func.avg(models.ActivityStream.altitude).label('avg_alt')
                ).filter(
                    models.ActivityStream.activity_id == activity_id,
                    models.ActivityStream.altitude.isnot(None)
                ).first()
                
                if altitude_stats and altitude_stats.avg_alt:
                    avg_alt = altitude_stats.avg_alt
                    min_alt = altitude_stats.min_alt or avg_alt
                    max_alt = altitude_stats.max_alt or avg_alt
                    
                    lines.append(f"\n🏔️ GERÇEK İRTİFA VERİSİ (GPS):")
                    lines.append(f"- Ortalama Rakım: {avg_alt:.0f} m")
                    lines.append(f"- Min/Max: {min_alt:.0f}m - {max_alt:.0f}m")
                    
                    if avg_alt > 1000:
                        lines.append(f"- ⚠️ YÜKSEK RAKIM! ({avg_alt:.0f}m > 1000m)")
                        lines.append("- Oksijen seviyesi deniz seviyesinin ~%85-90'ı")
                        lines.append("- Nabız deniz seviyesine göre %10-15 DAHA YÜKSEK olabilir")
                        lines.append("- Aynı efor daha zor hissedilir")
                    elif avg_alt > 500:
                        lines.append(f"- Orta rakım ({avg_alt:.0f}m)")
                        lines.append("- Hafif irtifa etkisi olabilir")
                    else:
                        lines.append(f"- Deniz seviyesine yakın ({avg_alt:.0f}m)")
                        lines.append("- Normal koşullar, baseline performans")
                    
                    # Elevation delta
                    if max_alt - min_alt > 100:
                        lines.append(f"- Toplam yükseliş farkı: {max_alt - min_alt:.0f}m (dalgalı parkur)")
            except Exception as e:
                pass  # Silent fail - don't break analysis if altitude query fails
        
        # HEALTH DATA FOR THAT DAY (HRV, Stress, Sleep)
        if activity_date:
            try:
                # HRV data from previous night
                # Try activity_date and day before (HRV is recorded overnight)
                hrv = self.db.query(models.HRVLog).filter(
                    models.HRVLog.user_id == user_id,
                    models.HRVLog.calendar_date == activity_date
                ).first()
                
                # If not found, try day before (HRV often recorded for previous night)
                if not hrv and isinstance(activity_date, date_type):
                    hrv = self.db.query(models.HRVLog).filter(
                        models.HRVLog.user_id == user_id,
                        models.HRVLog.calendar_date == activity_date - timedelta(days=1)
                    ).first()
                
                if hrv:
                    lines.append(f"\n💓 HRV VERİSİ (Önceki Gece):")
                    lines.append(f"- HRV Ortalaması: {hrv.last_night_avg} ms")
                    if hrv.status:
                        lines.append(f"- Durum: {hrv.status}")
                    if hrv.baseline_low and hrv.baseline_high:
                        lines.append(f"- Baseline Aralığı: {hrv.baseline_low}-{hrv.baseline_high} ms")
                
                # Stress data
                stress = self.db.query(models.StressLog).filter(
                    models.StressLog.user_id == user_id,
                    models.StressLog.calendar_date == activity_date
                ).first()
                
                if stress:
                    lines.append(f"\n😰 STRES VERİSİ:")
                    lines.append(f"- Ortalama Stres: {stress.avg_stress}")
                    lines.append(f"- Max Stres: {stress.max_stress}")
                    if stress.status:
                        lines.append(f"- Durum: {stress.status}")
                
                # Sleep data from previous night
                # Sleep from previous night (day before activity)
                sleep_date = activity_date - timedelta(days=1) if isinstance(activity_date, date_type) else activity_date
                sleep = self.db.query(models.SleepLog).filter(
                    models.SleepLog.user_id == user_id,
                    models.SleepLog.calendar_date >= sleep_date,
                    models.SleepLog.calendar_date <= activity_date
                ).order_by(models.SleepLog.calendar_date.desc()).first()
                
                if sleep:
                    lines.append(f"\n😴 UYKU VERİSİ (Önceki Gece):")
                    if sleep.sleep_score:
                        lines.append(f"- Uyku Skoru: {sleep.sleep_score}")
                    duration_hrs = sleep.duration_seconds / 3600 if sleep.duration_seconds else 0
                    lines.append(f"- Uyku Süresi: {duration_hrs:.1f} saat")
                    if sleep.deep_seconds:
                        deep_hrs = sleep.deep_seconds / 3600
                        lines.append(f"- Derin Uyku: {deep_hrs:.1f} saat")
                    if sleep.quality_score:
                        lines.append(f"- Kalite: {sleep.quality_score}")
                
                # CTL/ATL/TSB using the same formula as dashboard
                import training_load
                
                if activity_date:
                    # Get all activities for PMC calculation
                    all_activities = self.db.query(models.Activity).filter(
                        models.Activity.user_id == user_id
                    ).order_by(models.Activity.start_time_local).all()
                    
                    if all_activities:
                        # Convert to dict format expected by training_load
                        act_list = [
                            {
                                'local_start_date': a.local_start_date,
                                'start_time_local': a.start_time_local,
                                'duration': a.duration,
                                'average_hr': a.average_hr,
                                'distance': a.distance,
                                'elevation_gain': a.elevation_gain
                            }
                            for a in all_activities
                        ]
                        
                        # Use the same function as dashboard API
                        load_context = training_load.get_recent_load_context(
                            act_list,
                            activity_date,
                            lthr=165,
                            resting_hr=45
                        )
                        
                        ctl = load_context['ctl_before']
                        atl = load_context['atl_before']
                        tsb = load_context['tsb_before']
                        form_status = load_context['form_status']
                        
                        lines.append(f"\n📈 FORM DURUMU (O Gün):")
                        lines.append(f"- Fitness (CTL): {ctl:.0f}")
                        lines.append(f"- Yorgunluk (ATL): {atl:.0f}")
                        lines.append(f"- Form (TSB): {tsb:.0f}")
                        lines.append(f"- Durum: {form_status}")
                        
            except Exception as e:
                pass  # Silent fail
        
        # SHOE DATA
        if activity_id:
            try:
                activity = self.db.query(models.Activity).filter(
                    models.Activity.activity_id == activity_id
                ).first()
                
                if activity:
                    # Full weather data including wind
                    if activity.weather_temp is not None or activity.weather_wind_speed is not None:
                        lines.append(f"\n🌤️ HAVA DURUMU (Detaylı):")
                        if activity.weather_temp is not None:
                            lines.append(f"- Sıcaklık: {activity.weather_temp}°C")
                        if activity.weather_humidity is not None:
                            lines.append(f"- Nem: %{activity.weather_humidity}")
                        if activity.weather_wind_speed is not None:
                            lines.append(f"- Rüzgar: {activity.weather_wind_speed} km/h")
                        if activity.weather_condition:
                            lines.append(f"- Durum: {activity.weather_condition}")
                    
                    # Shoe data with total km
                    if activity.shoe_id and activity.shoe:
                        shoe = activity.shoe
                        # Calculate total distance on shoe
                        from sqlalchemy import func as sql_func
                        total_shoe_km = self.db.query(
                            sql_func.sum(models.Activity.distance)
                        ).filter(
                            models.Activity.shoe_id == shoe.id
                        ).scalar() or 0
                        total_shoe_km = total_shoe_km / 1000 + (shoe.initial_distance or 0)
                        
                        lines.append(f"\n👟 AYAKKABI:")
                        lines.append(f"- Model: {shoe.name}")
                        if shoe.brand:
                            lines.append(f"- Marka: {shoe.brand}")
                        lines.append(f"- Toplam Mesafe: {total_shoe_km:.1f} km")
                        if total_shoe_km > 700:
                            lines.append(f"- ⚠️ Ayakkabı yıpranmış olabilir (>700km)")
                        elif total_shoe_km > 500:
                            lines.append(f"- Ayakkabı orta kullanımda (500-700km)")
                            
            except Exception as e:
                pass  # Silent fail
        
        if pack.get('flags') and len(pack['flags']) > 0:
            lines.append(f"\nÖnemli Gözlemler:")
            for flag in pack['flags'][:5]:
                lines.append(f"- {flag}")
        
        if pack.get('tables'):
            lines.append(f"\n{pack['tables']}")  # Full tables - no truncation
            
        if pack.get('readiness') and pack['readiness'] != "Not in summary":
            lines.append(f"\nToparlanma Durumu:\n{pack['readiness']}")
            
        return "\n".join(lines)

    def _build_trend_context(self, stats, activity_count, anchor_date, health_data=None) -> str:
        """Build context for trend analysis including health data."""
        tsb = stats['tsb']
        
        # Interpret TSB
        if tsb > 15:
            form_status = "Çok dinlenmiş - belki biraz daha yüklenebilirsin"
        elif tsb > 0:
            form_status = "Yarış formu - ideal dinlenme seviyesi"
        elif tsb > -10:
            form_status = "Hafif yorgun ama iyi"
        elif tsb > -30:
            form_status = "Antrenman yükü altında - normal"
        else:
            form_status = "Dikkat! Aşırı yüklenme riski"
        
        context = f"""
SON HAFTA ÖZETİ ({anchor_date}):
- Koşu sayısı: {activity_count}
- Fitness (CTL): {stats['ctl']:.1f}
- Yorgunluk (ATL): {stats['atl']:.1f}
- Form (TSB): {tsb:.1f}

DURUM: {form_status}
"""
        
        # Add health data if available
        if health_data:
            health_lines = ["\nBUGÜN SAĞLIK VERİSİ:"]
            
            if health_data.get('sleep'):
                s = health_data['sleep']
                health_lines.append(f"- Uyku: {s.get('score', 'N/A')}/100, {s.get('duration_hrs', 0)} saat, Derin: {s.get('deep_pct', 0)}%")
            
            if health_data.get('hrv'):
                h = health_data['hrv']
                health_lines.append(f"- HRV: {h.get('value', 'N/A')} ms ({h.get('status', '')})")
            
            if health_data.get('stress'):
                st = health_data['stress']
                health_lines.append(f"- Stres: {st.get('avg', 'N/A')} ({st.get('status', '')})")
            
            if len(health_lines) > 1:  # Has actual data
                context += "\n".join(health_lines)
        
        return context

    def _format_conversation_history(self, history: List[tuple]) -> str:
        """Format conversation history for context."""
        if not history:
            return "(İlk mesaj)"
        
        lines = []
        for role, content in history[-3:]:  # Last 3 messages
            speaker = "Sporcu" if role == "user" else "Coach"
            # Truncate long messages
            short_content = content[:200] + "..." if len(content) > 200 else content
            lines.append(f"{speaker}: {short_content}")
        
        return "\n".join(lines)

    def _fetch_pack_from_db(self, user_id, activity_id) -> Optional[Dict]:
        """Fetch raw JSON from DB and build pack with full lap tables."""
        import models
        
        # First try to get full activity with raw_json for lap data
        activity = self.db.query(models.Activity).filter(
            models.Activity.activity_id == activity_id
        ).first()
        
        if activity and activity.raw_json:
            # Use pack builder for proper lap tables and running dynamics
            raw = activity.raw_json if isinstance(activity.raw_json, dict) else {}
            pack = self.pack_builder.build_pack(raw)
            return pack
        
        # Fallback to repo summary if no raw_json
        repo_act = self.repo.get_activity_summary(user_id, activity_id)
        if repo_act:
            return {
                "facts": repo_act.facts_text, 
                "tables": repo_act.summary_text or "Detay yok",
                "flags": [],
                "readiness": "Not in summary" 
            }
        return None

    def _get_health_for_date(self, user_id, date_val):
         return {}
