"""
Note Extractor Service
======================

Extracts health/life event notes from user messages using LLM.
Works in conjunction with the Athlete Knowledge System.

Key Features:
- Detects injuries, chronic conditions, lifestyle factors, mental state
- Returns structured ExtractedNote objects
- Asks for user confirmation before saving
- Matches detected conditions to known condition_types
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from coach_v2.llm_client import LLMClient, GeminiClient


# ============================================================================
# CONDITION DURATION RULES
# ============================================================================
# None = until resolved (no time limit)
# Number = days the condition should be considered after event_date

CONDITION_DURATION = {
    'chronic': None,        # Until resolved - tiroid, diyabet, astım
    'medical': None,        # Until resolved - tıbbi durumlar
    'injury': None,         # Until resolved + follow-up - sakatlıklar
    'lifestyle': 3,         # 3 days - alkol, kötü uyku  
    'mental': 14,           # 14 days - stres, burnout
    'environmental': 1,     # 1 day - hava durumu, rakım
    'life_event': 7,        # 7 days - seyahat, iş stresi
}

# Severity multiplier for duration (applied to non-None durations)
SEVERITY_MULTIPLIER = {
    1: 0.5,   # Hafif - shorter effect
    2: 0.75,  # Hafif-orta
    3: 1.0,   # Orta - standard
    4: 1.5,   # Orta-ciddi - longer effect
    5: 2.0,   # Ciddi - extended effect
}




@dataclass
class ExtractedNote:
    """A detected health/life event from user message."""
    condition_type: str          # e.g., 'shin_splint', 'alcohol', 'work_stress'
    category: str                # 'injury', 'chronic', 'lifestyle', 'mental', 'life_event'
    description: str             # LLM-generated description
    event_type: str              # 'onset', 'update', 'resolved', 'relapse'
    severity: int                # 1-5 scale
    confidence: float            # 0.0-1.0
    source: str = 'self_report'  # 'self_report', 'professional'
    raw_message: str = ''        # Original user message
    event_date_offset: int = 0   # Days from today (0=today, -1=yesterday, -7=last week)
    related_to_previous: bool = False  # True if this note is related to another note in same message
    existing_condition_id: Optional[str] = None  # UUID if linking to existing condition
    
    def to_dict(self) -> dict:
        return asdict(self)



# LLM Prompt for extracting notes from user messages
NOTE_EXTRACTION_PROMPT = """Sen bir koşu koçunun asistanısın. Kullanıcının mesajından sağlık, yaşam veya antrenmanı etkileyen bilgileri çıkar.

MESAJ: "{message}"

BAĞLAM (varsa): {context}

AKTİF DURUMLAR (varsa): {active_conditions}

# TESPİT EDİLECEK DURUMLAR

1. SAKATLIKLAR (injury):
   - shin_splint: Kaval kemiği ağrısı
   - knee_pain: Diz ağrısı
   - achilles: Aşil tendonu
   - plantar_fasciitis: Tabanlık/topuk ağrısı
   - muscle_strain: Kas zorlanması/çekmesi
   - back_pain: Bel/sırt ağrısı
   - general_injury: Diğer sakatlıklar

2. KRONİK DURUMLAR (chronic):
   - thyroid: Tiroid hastalığı
   - diabetes: Diyabet
   - asthma: Astım
   - heart_condition: Kalp rahatsızlığı

3. YAŞAM TARZI (lifestyle):
   - alcohol: Alkol tüketimi
   - poor_sleep: Kötü uyku
   - illness: Hastalık (grip, soğuk algınlığı)

4. MENTAL (mental):
   - work_stress: İş stresi
   - low_motivation: Düşük motivasyon
   - anxiety: Anksiyete/kaygı
   - burnout: Tükenmişlik

5. YAŞAM OLAYLARI (life_event):
   - new_job: Yeni iş ⚠️ "Yeni iş", "işe başladım", "iş değiştirdim", "yeni işe başladım" → KESİNLİKLE new_job kullan! 
     Eğer mesajda hem yeni iş HEM DE "yoğun", "stresli" varsa → SADECE new_job kaydet (work_stress DEĞİL!)
   - new_baby: Yeni bebek
   - pregnancy: Hamilelik


# OLAY TİPLERİ (event_type)
- onset: Yeni başlayan VEYA İLK KEZ SÖYLENİYOR ("bugün başladı", "ağrıyor", "yıllardır tiroidim var" - ilk kez söylüyor = onset!)
- update: SADECE daha önce söylenmiş durum hakkında güncelleme ("hâlâ ağrıyor", "biraz daha iyi")
- resolved: İyileşen durum ("geçti", "iyileştim", "artık ağrımıyor")
- relapse: Tekrarlayan durum ("yine başladı", "tekrar oldu") - ⚠️ AKTİF DURUMLAR'da resolved olan bir durum tekrar başlıyorsa relapse kullan!

⚠️ ÖNEMLİ: Kullanıcı bir durumu İLK KEZ bahsediyorsa (AKTİF DURUMLAR'da yoksa), bu HER ZAMAN "onset"tir! 
"Tiroid hastasıyım, yıllardır ilaç kullanıyorum" → Bu yeni bilgi, event_type: "onset" (update DEĞİL!)



# TARİH TESPİTİ (event_date_offset - gün olarak)
- 0 = bugün (default)
- -1 = dün
- -7 = geçen hafta
- -14 = 2 hafta önce
Örnek: "dün başladı" → event_date_offset: -1, "geçen hafta grip oldum" → event_date_offset: -7

# KAYNAK TESPİTİ (source)
- self_report: Kullanıcının kendi hissi/yorumu
- professional: Doktor/fizyoterapist/uzman görüşü ("doktor dedi ki", "fizyoterapist")

# ÇIKTI FORMATI (strict JSON)

Eğer mesajda önemli bir durum TESPİT EDİLDİYSE:
```json
{{
  "detected": true,
  "notes": [
    {{
      "condition_type": "shin_splint",
      "category": "injury",
      "description": "Kaval kemiğinde ağrı başlamış",
      "event_type": "onset",
      "event_date_offset": 0,
      "severity": 3,
      "confidence": 0.8,
      "source": "self_report",
      "related_to_previous": null
    }}
  ]
}}
```

Eğer mesajda önemli bir durum YOKSA:
```json
{{
  "detected": false,
  "notes": []
}}
```

# ÖNEMLİ KURALLAR
- Sadece antrenmanı/sağlığı ETKİLEYEN durumları çıkar
- "Bugün güzel koştum" gibi normal mesajları ignore et
- ⚠️ BELİRSİZLİK KURALI: Soru tarzında mesajlarda ("bu tükenmişlik mi?", "acaba şu mu?") confidence DÜŞÜK ver (0.4-0.6)
- Birden fazla durum varsa hepsini listele
- Aynı olaydan kaynaklanan durumları ilişkilendir (örn: "dün içtim ve uyuyamadım" → 2 note, related_to_previous: true)
- AKTİF DURUMLAR'da listelenen bir durum için güncelleme geliyorsa, aynı condition ismini kullan
- JSON dışında hiçbir şey yazma

# EDGE CASE KURALLARI (KRİTİK!)

1. ⛔ POZİTİF BAĞLAM = KESİNLİKLE TESPİT ETME:
   - Bu kural EN ÖNCELİKLİ kuraldır, diğer kurallardan önce gelir!
   - Mesajda pozitif kelimeler ("güzel", "güzeldi", "harika", "süper", "iyi", "mükemmel") varsa VE sonra hafif şikayetler ("yoruldum", "biraz ağrı", "bacaklar yoruldu", "kas ağrısı") varsa:
     → detected: false (kesinlikle tespit ETME!)
   - Bu normal antrenman sonrası yorgunluktur, sağlık durumu DEĞİL!
   - ✓ "Koşu güzeldi ama yoruldum" → detected: false
   - ✓ "Harika antrenman, biraz kas ağrısı var" → detected: false
   - ✓ "Süper bir koşuydu, sadece bacaklar yoruldu" → detected: false
   - ✓ "İyi geçti ama biraz yorgunum" → detected: false


2. ✅ "İYİLEŞİYORUM" = UPDATE:
   - Mesajda "iyileşiyorum", "geçiyor", "daha iyi", "azaldı" ifadeleri varsa → event_type: "update" (onset DEĞİL!)
   - Örnek: "Grip oldum ama iyileşiyorum" → event_type: "update"
   - Örnek: "Diz ağrım azaldı" → event_type: "update"

3. ⚠️ DİSMİSSİVE DİL = ÇOK DÜŞÜK CONFIDENCE:
   - Mesajda "önemli değil", "geçer", "bir şey yok", "sorun değil" ifadeleri varsa → confidence: 0.3-0.4
   - Örnek: "Hafif ağrı var ama önemli değil sanırım" → confidence: 0.3
   - Kullanıcı kendisi önemsiz diyorsa, biz de düşük öncelik vermeliyiz

JSON:

"""



class NoteExtractor:
    """
    Extracts health/life notes from user messages using LLM.
    """
    
    def __init__(self, db: Session, llm_client: LLMClient):
        self.db = db
        self.llm = llm_client
        # Cache condition types from DB
        self._condition_types = self._load_condition_types()
    
    def _load_condition_types(self) -> Dict[str, Dict]:
        """Load condition types from database for matching."""
        try:
            result = self.db.execute(text("""
                SELECT id, name, category, impact_level, default_followup_days, description
                FROM coach_v2.condition_types
            """))
            types = {}
            for row in result:
                types[row[1]] = {
                    'id': row[0],
                    'name': row[1],
                    'category': row[2],
                    'impact_level': row[3],
                    'followup_days': row[4],
                    'description': row[5]
                }
            return types
        except Exception as e:
            logging.error(f"Failed to load condition types: {e}")
            return {}
    
    def extract_notes(self, message: str, context: str = "", user_id: int = None, 
                       discussed_activity_date = None, discussed_activity_name: str = None) -> List[ExtractedNote]:
        """
        Extract health/life notes from user message.
        
        Args:
            message: User's message text
            context: Optional conversation context
            user_id: User ID for looking up active conditions (for relapse detection)
            discussed_activity_date: Date of the activity being discussed (for relative date references)
            discussed_activity_name: Name of the activity being discussed
            
        Returns:
            List of ExtractedNote objects (empty if nothing detected)

        """
        if not message or len(message.strip()) < 5:
            return []
        
        # Skip messages that are clearly just greetings or simple queries
        skip_patterns = ['selam', 'merhaba', 'günaydın', 'son koşumu', 'analiz et', 'nasıldım']
        if any(p in message.lower() for p in skip_patterns) and len(message) < 30:
            return []
        
        # Get active conditions for this user (for relapse detection)
        active_conditions_text = "(Yok)"
        active_conditions_map = {}  # condition_type -> condition_id mapping
        if user_id:
            try:
                active_conditions = self.get_active_conditions(user_id)
                if active_conditions:
                    cond_lines = []
                    for c in active_conditions:
                        cond_lines.append(f"- {c['condition_name']}: {c['description']} (event_type: {c['event_type']}, {c['days_since']} gün önce)")
                        active_conditions_map[c['condition_name']] = c['condition_id']
                    active_conditions_text = "\n".join(cond_lines)
            except Exception as e:
                logging.warning(f"Failed to get active conditions: {e}")
        
        # Build discussed activity context (for relative date references like "o günden önceki gün")
        discussed_context = ""
        if discussed_activity_date and discussed_activity_name:
            from datetime import date, timedelta
            today = date.today()
            days_diff = (today - discussed_activity_date).days
            discussed_context = f"""
KONUŞULAN AKTİVİTE: {discussed_activity_name} ({discussed_activity_date})
- "O gün" = {discussed_activity_date}
- "O günden önceki gün" = {discussed_activity_date - timedelta(days=1)}
- Bugün = {today}
Eğer kullanıcı "o günden önceki gün" gibi referans veriyorsa, event_date_offset'i buna göre hesapla!
Örnek: Bugün {today}, konuşulan aktivite {discussed_activity_date} → "o günden önceki gün" = -{days_diff + 1} gün offset
"""
        
        prompt = NOTE_EXTRACTION_PROMPT.format(
            message=message,
            context=context if context else "(Bağlam yok)",
            active_conditions=active_conditions_text
        )
        
        # Inject discussed activity context at the beginning of the prompt
        if discussed_context:
            prompt = prompt.replace("MESAJ:", f"{discussed_context}\nMESAJ:")

        
        try:
            response = self.llm.generate(prompt, max_tokens=500)
            notes = self._parse_response(response.text, message)
            
            # Link notes to existing conditions if applicable
            for note in notes:
                if note.condition_type in active_conditions_map:
                    # This is an update/resolved/relapse for an existing condition
                    note.existing_condition_id = active_conditions_map[note.condition_type]
            
            return notes
        except Exception as e:
            logging.error(f"Note extraction failed: {e}")
            return []

    
    def _parse_response(self, response_text: str, raw_message: str) -> List[ExtractedNote]:
        """Parse LLM response into ExtractedNote objects."""
        import re
        
        try:
            # Extract JSON from response - try multiple patterns
            text = response_text.strip()
            
            # Pattern 1: ```json ... ```
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            # Pattern 2: ``` ... ```
            elif "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1].strip()
            # Pattern 3: Raw JSON starting with {
            elif text.startswith("{"):
                pass  # Already clean
            # Pattern 4: Try to find JSON object with regex
            else:
                json_match = re.search(r'\{[^{}]*"detected"[^{}]*\}', text, re.DOTALL)
                if json_match:
                    text = json_match.group()
                else:
                    # No JSON found - check if LLM said "no detection"
                    no_detect_patterns = ['detected": false', 'hiçbir', 'tespit edilmedi', 'normal mesaj']
                    if any(p in text.lower() for p in no_detect_patterns):
                        return []
                    logging.warning(f"No JSON pattern found in response: {text[:100]}...")
                    return []
            
            data = json.loads(text)
            
            if not data.get('detected', False):
                return []
            
            notes = []
            for note_data in data.get('notes', []):
                # Validate condition type exists
                condition_type = note_data.get('condition_type', 'general_injury')
                if condition_type not in self._condition_types:
                    # Try to find closest match or use general
                    condition_type = self._find_closest_type(condition_type, note_data.get('category', 'injury'))
                
                note = ExtractedNote(
                    condition_type=condition_type,
                    category=note_data.get('category', 'injury'),
                    description=note_data.get('description', ''),
                    event_type=note_data.get('event_type', 'onset'),
                    severity=min(5, max(1, note_data.get('severity', 3))),
                    confidence=min(1.0, max(0.0, note_data.get('confidence', 0.7))),
                    source=note_data.get('source', 'self_report'),
                    raw_message=raw_message,
                    event_date_offset=note_data.get('event_date_offset', 0),
                    related_to_previous=note_data.get('related_to_previous', False) or False
                )
                notes.append(note)
            
            return notes

            
        except json.JSONDecodeError as e:
            logging.warning(f"JSON parse error (will retry): {e}")
            # Try to extract detected=false pattern
            if '"detected": false' in response_text or '"detected":false' in response_text:
                return []
            logging.error(f"Failed to parse note extraction response: {e}")
            return []
        except Exception as e:
            logging.error(f"Error processing extracted notes: {e}")
            return []

    
    def _find_closest_type(self, condition_type: str, category: str) -> str:
        """Find the closest matching condition type in the database."""
        # First, look for types in the same category
        category_types = [t for t, v in self._condition_types.items() if v['category'] == category]
        
        if category_types:
            # Return first match in category
            return category_types[0]
        
        # Fallback to general types
        fallbacks = {
            'injury': 'general_injury',
            'chronic': 'thyroid',
            'lifestyle': 'illness',
            'mental': 'work_stress',
            'life_event': 'new_job'
        }
        return fallbacks.get(category, 'general_injury')
    
    def generate_confirmation_prompt(self, notes: List[ExtractedNote]) -> str:
        """
        Generate a confirmation message to ask user.
        
        Returns a Turkish message asking user to confirm the detected notes.
        """
        if not notes:
            return ""
        
        if len(notes) == 1:
            note = notes[0]
            severity_text = {1: "hafif", 2: "hafif-orta", 3: "orta", 4: "orta-ciddi", 5: "ciddi"}
            
            # Only ask source question for injury/chronic conditions where professional diagnosis matters
            # Skip for lifestyle (alcohol, sleep) and mental (stress) - obviously self-report
            should_ask_source = note.category in ['injury', 'chronic'] and note.source == 'self_report'
            source_question = "\n\nBu bilgi doktor/fizyoterapist gibi bir uzmandan mı geliyor?" if should_ask_source else ""
            
            return f"""Anladığım kadarıyla "{note.description}" durumun var. 

Bunu hatırlamamı ve takip etmemi ister misin? (Evet/Hayır){source_question}"""
        
        else:
            lines = ["Birkaç şey not aldım:"]
            for i, note in enumerate(notes, 1):
                lines.append(f"{i}. {note.description}")
            lines.append("\nBunları takip etmemi ister misin?")
            return "\n".join(lines)

    
    def save_note(
        self, 
        user_id: int, 
        note: ExtractedNote, 
        condition_id: Optional[str] = None
    ) -> bool:
        """
        Save an extracted note to the database.
        
        Args:
            user_id: User ID
            note: ExtractedNote to save
            condition_id: UUID for existing condition (for updates/resolved) or None for new
            
        Returns:
            True if saved successfully
        """
        from datetime import timedelta
        
        try:
            # Get condition type ID
            ct = self._condition_types.get(note.condition_type, {})
            condition_type_id = ct.get('id')
            
            # Determine condition_id:
            # 1. Use explicit parameter if provided
            # 2. Use existing_condition_id from note (linked to active condition)
            # 3. Generate new UUID for new conditions
            if not condition_id:
                condition_id = note.existing_condition_id or str(uuid.uuid4())
            
            # Calculate actual event date using offset
            event_date = date.today() + timedelta(days=note.event_date_offset)
            
            # Calculate next follow-up date
            followup_days = ct.get('followup_days', [3, 7])
            next_followup = None
            if followup_days and note.event_type not in ['resolved']:
                next_followup = (date.today() + timedelta(days=followup_days[0])).isoformat()
            
            self.db.execute(text("""
                INSERT INTO coach_v2.athlete_health_log 
                (user_id, condition_id, condition_type_id, event_type, event_date, 
                 description, source, confidence, severity, raw_message, 
                 needs_followup, followup_scheduled_date)
                VALUES 
                (:user_id, :condition_id, :type_id, :event_type, :event_date,
                 :description, :source, :confidence, :severity, :raw_message,
                 :needs_followup, :followup_date)
            """), {
                "user_id": user_id,
                "condition_id": condition_id,
                "type_id": condition_type_id,
                "event_type": note.event_type,
                "event_date": event_date.isoformat(),
                "description": note.description,
                "source": note.source,
                "confidence": note.confidence,
                "severity": note.severity,
                "raw_message": note.raw_message,
                "needs_followup": note.event_type not in ['resolved'],
                "followup_date": next_followup
            })
            self.db.commit()
            
            logging.info(f"Saved health note for user {user_id}: {note.condition_type} (event_date: {event_date})")
            return True

            
        except Exception as e:
            logging.error(f"Failed to save health note: {e}")
            self.db.rollback()
            return False
    
    def get_active_conditions(self, user_id: int, target_date: date = None) -> List[Dict]:
        """
        Get active conditions for a user with impact-based aging.
        
        Args:
            user_id: User ID
            target_date: Date to check conditions for (default: today)
            
        Returns:
            List of active condition dicts
        """
        if target_date is None:
            target_date = date.today()
        
        try:
            result = self.db.execute(text("""
                SELECT 
                    ac.condition_id,
                    ac.condition_name,
                    ac.category,
                    ac.impact_level,
                    ac.event_type,
                    ac.event_date,
                    ac.description,
                    ac.severity,
                    (:target_date - ac.event_date) as days_since
                FROM coach_v2.active_conditions ac
                WHERE ac.user_id = :user_id
                AND (
                    -- Chronic: ALWAYS include
                    ac.impact_level = 'chronic'
                    OR
                    -- Recurring: Include if within 180 days
                    (ac.impact_level = 'recurring' AND ac.event_date > :target_date - INTERVAL '180 days')
                    OR
                    -- Acute: Include if within 30 days
                    (ac.impact_level = 'acute' AND ac.event_date > :target_date - INTERVAL '30 days')
                )
                AND ac.event_type != 'resolved'
                ORDER BY 
                    CASE ac.impact_level WHEN 'chronic' THEN 1 WHEN 'recurring' THEN 2 ELSE 3 END,
                    ac.event_date DESC
            """), {"user_id": user_id, "target_date": target_date})
            
            conditions = []
            for row in result:
                conditions.append({
                    'condition_id': str(row[0]),
                    'condition_name': row[1],
                    'category': row[2],
                    'impact_level': row[3],
                    'event_type': row[4],
                    'event_date': str(row[5]),
                    'description': row[6],
                    'severity': row[7],
                    'days_since': row[8]
                })
            
            return conditions
            
        except Exception as e:
            logging.error(f"Failed to get active conditions: {e}")
            return []
    
    def get_conditions_needing_followup(self, user_id: int) -> List[Dict]:
        """
        Get conditions that need follow-up (for proactive coaching).
        
        Returns conditions where:
        - Resolved recently (3-7 days) - need verification
        - Scheduled follow-up is due
        - No update in 7+ days
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    ac.condition_id,
                    ac.condition_name,
                    ac.category,
                    ac.event_type,
                    ac.event_date,
                    ac.description,
                    (CURRENT_DATE - ac.event_date) as days_since,
                    CASE 
                        WHEN ac.event_type = 'resolved' AND (CURRENT_DATE - ac.event_date) BETWEEN 3 AND 7 
                            THEN 'resolved_verification'
                        WHEN ac.event_type != 'resolved' AND ac.needs_followup AND ac.followup_scheduled_date <= CURRENT_DATE
                            THEN 'scheduled_followup'
                        WHEN ac.event_type != 'resolved' AND (CURRENT_DATE - ac.event_date) >= 7
                            THEN 'overdue_check'
                        ELSE NULL
                    END as followup_reason
                FROM coach_v2.active_conditions ac
                WHERE ac.user_id = :user_id
                AND (
                    (ac.event_type = 'resolved' AND (CURRENT_DATE - ac.event_date) BETWEEN 3 AND 7)
                    OR
                    (ac.event_type != 'resolved' AND ac.needs_followup AND ac.followup_scheduled_date <= CURRENT_DATE)
                    OR
                    (ac.event_type != 'resolved' AND (CURRENT_DATE - ac.event_date) >= 7)
                )
                ORDER BY ac.event_date
            """), {"user_id": user_id})
            
            conditions = []
            for row in result:
                if row[7]:  # Only if followup_reason exists
                    conditions.append({
                        'condition_id': str(row[0]),
                        'condition_name': row[1],
                        'category': row[2],
                        'event_type': row[3],
                        'event_date': str(row[4]),
                        'description': row[5],
                        'days_since': row[6],
                        'followup_reason': row[7]
                    })
            
            return conditions
            
        except Exception as e:
            logging.error(f"Failed to get conditions needing followup: {e}")
            return []
    
    def get_conditions_around_date(self, user_id: int, target_date, days_before: int = 3, days_after: int = 0) -> List[Dict]:
        """
        Get conditions around a specific date (e.g., activity date).
        
        This is used to correlate health conditions with activity performance.
        For example, if user had alcohol the day before a run, show that in analysis.
        
        Args:
            user_id: User ID
            target_date: The activity date to check around
            days_before: How many days before to check (default 3)
            days_after: How many days after to check (default 0)
            
        Returns:
            List of conditions in the date range
        """
        if not target_date:
            return []
            
        try:
            from datetime import timedelta
            
            start_date = target_date - timedelta(days=days_before)
            end_date = target_date + timedelta(days=days_after)
            
            result = self.db.execute(text("""
                SELECT 
                    ahl.condition_id,
                    ct.name as condition_name,
                    ct.category,
                    ahl.event_type,
                    ahl.event_date,
                    ahl.description,
                    ahl.severity,
                    ct.affects_training
                FROM coach_v2.athlete_health_log ahl
                LEFT JOIN coach_v2.condition_types ct ON ahl.condition_type_id = ct.id
                WHERE ahl.user_id = :user_id
                AND ahl.event_date BETWEEN :start_date AND :end_date
                AND ahl.event_type != 'resolved'
                ORDER BY ahl.event_date DESC
            """), {
                "user_id": user_id, 
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            })
            
            conditions = []
            for row in result:
                conditions.append({
                    'condition_id': str(row[0]),
                    'condition_name': row[1],
                    'category': row[2],
                    'event_type': row[3],
                    'event_date': row[4],
                    'description': row[5],
                    'severity': row[6],
                    'affects_training': row[7]
                })
            
            return conditions
            
        except Exception as e:
            logging.error(f"Failed to get conditions around date {target_date}: {e}")
            return []
    
    def format_conditions_for_context(self, conditions: List[Dict]) -> str:

        """Format conditions as context string for LLM prompts."""
        if not conditions:
            return ""
        
        lines = ["📋 SPORCU DURUMU:"]
        
        # Group by category
        chronic = [c for c in conditions if c['impact_level'] == 'chronic']
        active = [c for c in conditions if c['impact_level'] != 'chronic']
        
        if chronic:
            lines.append("\n⚠️ KRONİK DURUMLAR (Her zaman göz önünde bulundur):")
            for c in chronic:
                lines.append(f"  - {c['description']}")
        
        if active:
            lines.append("\n📍 AKTİF DURUMLAR:")
            for c in active:
                days = c.get('days_since', 0)
                lines.append(f"  - {c['description']} ({days} gün önce belirtildi)")
        
        return "\n".join(lines)

    def get_relevant_conditions_for_activity(self, user_id: int, activity_date) -> List[Dict]:
        """
        Get conditions relevant to an activity based on category and severity.
        
        This is the MAIN method for getting conditions to show during activity analysis.
        Uses dynamic duration rules:
        - Chronic/injury: Until resolved (no time limit)
        - Lifestyle: 3 days * severity_multiplier
        - Mental: 14 days * severity_multiplier
        - Environmental: 1 day
        
        Args:
            user_id: User ID
            activity_date: The activity date to check conditions for
            
        Returns:
            List of relevant conditions with their context
        """
        if not activity_date:
            return []
            
        try:
            from datetime import timedelta
            
            # Query all non-resolved conditions with their category info
            result = self.db.execute(text("""
                SELECT 
                    ahl.condition_id,
                    ct.name as condition_name,
                    ct.category,
                    ahl.event_type,
                    ahl.event_date,
                    ahl.description,
                    ahl.severity,
                    ct.affects_training,
                    ct.id as condition_type_id
                FROM coach_v2.athlete_health_log ahl
                LEFT JOIN coach_v2.condition_types ct ON ahl.condition_type_id = ct.id
                WHERE ahl.user_id = :user_id
                AND ahl.event_type != 'resolved'
                ORDER BY ahl.event_date DESC
            """), {"user_id": user_id})
            
            relevant_conditions = []
            
            for row in result:
                condition_id = str(row[0])
                category = row[2] or 'lifestyle'  # default to lifestyle if unknown
                event_date = row[4]
                severity = row[6] or 3
                description = row[5]
                
                # Convert event_date to date if string
                if isinstance(event_date, str):
                    from datetime import datetime as dt
                    event_date = dt.strptime(event_date, '%Y-%m-%d').date()
                
                # Get base duration for this category
                base_duration = CONDITION_DURATION.get(category, 7)  # default 7 days
                
                # Calculate if this condition is still relevant
                is_relevant = False
                days_diff = (activity_date - event_date).days if event_date else 0
                
                if base_duration is None:
                    # Chronic/injury - always relevant until resolved
                    is_relevant = True
                else:
                    # Apply severity multiplier
                    multiplier = SEVERITY_MULTIPLIER.get(severity, 1.0)
                    effective_duration = int(base_duration * multiplier)
                    
                    # Check if condition is within the effective window
                    is_relevant = days_diff <= effective_duration and days_diff >= 0
                
                if is_relevant:
                    time_ref = "aynı gün" if days_diff == 0 else f"{days_diff} gün önce"
                    relevant_conditions.append({
                        'condition_id': condition_id,
                        'condition_name': row[1],
                        'category': category,
                        'event_type': row[3],
                        'event_date': event_date,
                        'description': description,
                        'severity': severity,
                        'affects_training': row[7],
                        'days_since': days_diff,
                        'time_ref': time_ref,
                        'is_chronic': base_duration is None
                    })
            
            logging.info(f"Found {len(relevant_conditions)} relevant conditions for {activity_date} (user {user_id})")
            return relevant_conditions
            
        except Exception as e:
            logging.error(f"Failed to get relevant conditions for activity {activity_date}: {e}")
            import traceback
            traceback.print_exc()
            return []
