"""
Coach V2 Orchestrator (Humanized Rewrite)
==========================================

A conversational, memory-aware running coach with deep expertise.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging

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
from coach_v2.smart_query_engine import SmartQueryEngine

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
    
    COACH_PERSONA = """Sen deneyimli bir koşu koçusun. 15+ yıl elit ve amatör koşucularla çalıştın.

KİMLİĞİN:
- İsmin Coach. Samimi ama profesyonelsin.
- Koşucunun hem fiziksel hem mental durumunu önemsiyorsun.
- Veri okumada ustasın ama sayıları ezberletmezsin, hikaye anlatırsın.
- Motivasyon verirken gerçekçisin - boş övgü yapmaz, somut gelişimi gösterirsin.

İLETİŞİM TARZI:
- Doğal konuş, arkadaş gibi. Ama saçmalama.
- Kısa cümleler kur. Paragraflar 2-3 cümleyi geçmesin.
- Emoji kullanabilirsin ama abartma (max 1-2 per message).
- "Sen" diye hitap et, "siz" resmi.
- Soru sor, merak et, takip et.

ASLA YAPMA:
- Veri yokken sayı uydurma. "Verine bakmam lazım" de.
- Robotik format (VERİ: / ANALİZ: gibi) kullanma.
- Aynı cümleleri tekrarlama.
- Uzun paragraflar yazma.
"""

    RUNNING_EXPERTISE = """
KOŞU BİLGİSİ (gerektiğinde kullan):

NABIZ BÖLGELERİ:
- Zone 1-2 (<%70 MaxHR): Recovery, konuşarak koşulur
- Zone 3 (%70-80): Tempo, "comfortably hard"
- Zone 4 (%80-90): Threshold, laktat eşiği
- Zone 5 (>%90): VO2max, max 5-10dk

TEMEL KAVRAMLAR:
- Cardiac Drift: Süre uzadıkça nabız artar (dehidrasyon, sıcak, yorgunluk)
- Negative Split: İkinci yarı daha hızlı - ideal strateji
- RPE (1-10): Algılanan zorluk. 6-7 = rahat, 8-9 = zor, 10 = maksimum

YÜKLENME METRİKLERİ:
- CTL (Fitness): 42 günlük ortalama yük. Yüksek = form iyi
- ATL (Fatigue): 7 günlük ortalama yük. Yüksek = yorgun
- TSB (Form): CTL - ATL. Pozitif = dinlenmiş, negatif = yorgun
  - TSB -10 ile -30 arası: Antrenman bloğu
  - TSB 0 ile +15: Yarış formu (taper)
  - TSB < -30: Aşırı yüklenme riski

PACE REHBERİ (yaklaşık):
- Easy: Maraton pace + 1:00-1:30/km
- Tempo: Half marathon pace
- Threshold: 10K pace
- Interval: 5K pace veya daha hızlı
"""

    GREETING_RESPONSE = """Selam! 👋 

Bugün sana nasıl yardımcı olabilirim? Son antrenmanını konuşabiliriz, haftalık yüklenmeye bakabiliriz, ya da aklındaki herhangi bir soru varsa onu tartışabiliriz."""

    NO_DATA_RESPONSE = """Hmm, şu an elimde analiz edecek veri yok. 

Birkaç seçenek var:
- "Son koşumu analiz et" diyebilirsin
- Belirli bir tarih sorabilirsin (örn: "3 Aralık'taki koşu")
- Ya da formun hakkında konuşabiliriz ("Bu hafta nasıldı?")

Ne yapmak istersin?"""

    def __init__(self, db: Session, llm_client: LLMClient):
        self.db = db
        self.repo = CoachV2Repository(db)
        self.llm = llm_client
        self.retriever = CandidateRetriever(db)
        self.state_manager = ConversationStateManager(db)
        self.load_engine = TrainingLoadEngine(db)
        self.pack_builder = AnalysisPackBuilder()
        self.extractor = TargetedExtractor()
        self.evidence_gate = EvidenceGate()
        self.performance_analyzer = PerformanceAnalyzer(db)
        self.memory_store = AthleteMemoryStore(db)
        self.smart_engine = SmartQueryEngine(db, llm_client)
    
    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Handle chat request with pinned state awareness."""
        debug_info = {} if request.debug else None
        
        # 1. Get pinned state
        pinned_state = self.state_manager.get_pinned_state(request.user_id)
        
        # 2. Parse query
        parsed_intent = parse_user_query(request.message, pinned_state)
        
        if debug_info is not None:
            debug_info['intent_type'] = parsed_intent.intent_type
            debug_info['pinned_activity_id'] = pinned_state.garmin_activity_id
        
        # 3. Route
        response = self._route_intent(request, parsed_intent, pinned_state, debug_info)
        return response

    def _route_intent(self, request, parsed_intent, pinned_state, debug_info):
        """Route parsed intent to appropriate handler."""
        
        if parsed_intent.intent_type == 'greeting':
            return self._handle_greeting(request, debug_info)
        
        # Case A: Explicit Activity ID provided (Frontend Context)
        if request.garmin_activity_id:
             return self._handle_specific_activity(request, request.garmin_activity_id, parsed_intent, debug_info)

        # Case B: Date Query -> Resolve & Pin
        if parsed_intent.intent_type == 'specific_date':
            return self._handle_date_query(request, parsed_intent, debug_info)
        
        # Case C: Trend/Status Query
        if parsed_intent.intent_type == 'trend':
            return self._handle_trend_query(request, parsed_intent, debug_info)
        
        # Case C2: Race Strategy Query
        if parsed_intent.intent_type == 'race_strategy':
            return self._handle_race_strategy(request, parsed_intent, debug_info)
        
        # Case C3: Temporal Query ("neden şubat'ta formsuzdum?")
        if parsed_intent.intent_type == 'temporal_query':
            return self._handle_temporal_query(request, parsed_intent, debug_info)
        
        # Case C4: Progression Query ("VO2max nasıl gelişti?")
        if parsed_intent.intent_type == 'progression_query':
            return self._handle_progression_query(request, parsed_intent, debug_info)
        
        # Case D: Longitudinal (uses pinned date/load)
        if parsed_intent.intent_type == 'longitudinal_prep':
            return self._handle_longitudinal_query(request, parsed_intent, pinned_state, debug_info)
        
        # Case E: Health (uses pinned date)
        if parsed_intent.intent_type == 'health_day_status':
            return self._handle_health_query(request, parsed_intent, pinned_state, debug_info)
            
        # Case F: Follow-up Analysis (laps, technique, general) -> Needs Context
        if parsed_intent.intent_type in ['activity_analysis', 'laps_or_splits', 'technique']:
             return self._handle_activity_followup(request, parsed_intent, pinned_state, debug_info)

        # Case G: Last Activity
        if parsed_intent.intent_type == 'last_activity':
            return self._handle_last_activity(request, parsed_intent, debug_info)

        # Case H: Specific Activity Name (e.g., "Almada koşusu")
        if parsed_intent.intent_type == 'specific_name':
            return self._handle_name_query(request, parsed_intent, debug_info)

        # General - try to help
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

    def _handle_general_query(self, request, debug_info):
        """Handle general questions with LLM-driven smart query engine."""
        # Use SmartQueryEngine for flexible question answering
        try:
            response_text, smart_debug = self.smart_engine.analyze_and_answer(
                request.user_id, 
                request.message
            )
            if debug_info is not None:
                debug_info['smart_query'] = smart_debug
            return ChatResponse(message=response_text, debug_metadata=debug_info)
        except Exception as e:
            logging.error(f"SmartQueryEngine failed: {e}")
            return ChatResponse(message=self.NO_DATA_RESPONSE, debug_metadata=debug_info)

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
        context = self._build_activity_context(pack, activity_name, date_val, activity_id=act_id)
        
        # Include conversation history for continuity
        history_context = self._format_conversation_history(request.conversation_history)
        
        # Get athlete memory brief for context
        try:
            memory = self.memory_store.get_memory(request.user_id)
            athlete_brief = memory.career.to_brief() if memory.career else ""
        except Exception:
            athlete_brief = ""
        
        if wants_detail:
            word_limit = "300-400"
            detail_instruction = """
- DETAYLI ANALİZ İSTENİYOR - ekstra derinlemesine bak:
  * Lap bazında performans değişimi
  * Nabız bölge dağılımı
  * Kadans ve stride length değerlendirmesi
  * Önceki koşularla karşılaştırma
  * Spesifik iyileştirme önerileri
"""
        else:
            word_limit = "150-200"
            detail_instruction = """
- Veriyi hikaye gibi anlat, tablo formatı kullanma.
- Önemli noktaları vurgula ama her detayı sayma.
- Elevation verisi varsa değerlendir (tırmanış nabzı etkisi).
- Hava durumu verisi varsa performansa etkisini değerlendir.
- Yüksek rakım koşusuysa (Kapadokya, Bolu vb) bunu belirt.
- Sonda bir soru sor veya öneri ver.
"""
        
        prompt = f"""{self.COACH_PERSONA}

{self.RUNNING_EXPERTISE}

# SENİ TANIYORUM
{athlete_brief}

# SOHBET GEÇMİŞİ
{history_context}

# AKTİVİTE VERİSİ
{context}

# SPORCU SORUSU
{request.message}

# TALİMAT
{detail_instruction}
- {word_limit} kelime civarı tut.
"""
        
        max_tokens = 800 if wants_detail else 500
        resp = self.llm.generate(prompt, max_tokens=max_tokens)
        
        # Light validation - don't reject, just log
        is_valid, violation = self.evidence_gate.validate(resp.text, context + "\n" + request.message)
        if not is_valid:
            logging.warning(f"Potential hallucination: {violation}")
            
        return ChatResponse(
            message=resp.text, 
            resolved_activity_id=act_id, 
            resolved_date=str(date_val) if date_val else None, 
            debug_metadata=debug_info
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
             
        return ChatResponse(
            message=resp.text, 
            resolved_activity_id=activity_id, 
            resolved_date=str(date_val) if date_val else None, 
            debug_metadata=debug_info
        )

    # ==========================================================================
    # CONTEXT BUILDERS
    # ==========================================================================
    
    def _build_activity_context(self, pack, activity_name, activity_date, activity_id=None) -> str:
        """Build rich context from activity pack including real elevation and weather."""
        import models
        from sqlalchemy import func
        
        lines = [f"Aktivite: {activity_name}"]
        if activity_date:
            lines.append(f"Tarih: {activity_date}")
        
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
        
        if pack.get('flags') and len(pack['flags']) > 0:
            lines.append(f"\nÖnemli Gözlemler:")
            for flag in pack['flags'][:5]:
                lines.append(f"- {flag}")
        
        if pack.get('tables'):
            lines.append(f"\nDetay:\n{pack['tables'][:800]}")
            
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
        """Fetch raw JSON from DB and build pack on fly."""
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
