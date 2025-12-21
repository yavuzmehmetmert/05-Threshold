"""
AI Intent Classifier (Enhanced)
================================

Uses Gemini Flash for fast intent classification.
Returns structured JSON with:
- intent: handler name
- entities: extracted entities (date, metric, etc.)
- confidence: 0.0-1.0
"""

import os
import json
import re
import google.generativeai as genai
from typing import Literal, Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


# Handler types
HandlerType = Literal[
    "welcome_intent",
    "small_talk_intent", 
    "farewell_intent",
    "sohbet_handler",
    "db_handler",
    "training_detail_handler"
]

# Valid handlers for validation
VALID_HANDLERS = {
    "welcome_intent",
    "small_talk_intent",
    "farewell_intent",
    "sohbet_handler", 
    "db_handler",
    "training_detail_handler"
}


@dataclass
class IntentResult:
    """Structured intent classification result."""
    intent: str                          # Handler type
    entities: Dict[str, Any] = field(default_factory=dict)  # Extracted entities
    confidence: float = 0.9              # Confidence score
    
    def to_dict(self) -> dict:
        return asdict(self)


# Enhanced classification prompt with conversation history and JSON output
CLASSIFICATION_PROMPT = """Sen bir koşu asistanı intent sınıflandırıcısısın.

{conversation_history}

SON MESAJ: "{message}"

GÖREV: Mesajı analiz et ve aşağıdaki JSON formatında cevap ver:

```json
{{
  "intent": "<handler_name>",
  "entities": {{
    "date": "<tarih varsa: today, yesterday, last_week, veya spesifik tarih>",
    "metric": "<metrik varsa: pace, distance, hr, power, cadence, time>",
    "comparison": "<karşılaştırma varsa: trend, vs_previous, weekly, monthly>",
    "activity_ref": "<aktivite referansı: last, this, specific>"
  }},
  "confidence": <0.0-1.0 arası güven skoru>
}}
```

HANDLER TİPLERİ:
- welcome_intent: Selamlama (selam, merhaba, hey, iyi günler)
- small_talk_intent: Hal hatır (nasılsın, naber, keyifler)
- farewell_intent: Vedalaşma (hoşçakal, görüşürüz, bye)
- sohbet_handler: Genel sohbet, tavsiye, koşu hakkında bilgi
- db_handler: İstatistik, trend, karşılaştırma (kaç km, ortalama, toplam, haftalık)
- training_detail_handler: Spesifik antrenman analizi (son koşu, dünkü koşu, bu koşu, analiz et)

ENTITY KURALLARI:
- date: Sadece tarih/zaman referansı varsa doldur (dün, geçen hafta, 3 gün önce)
- metric: Sadece spesifik metrik soruluyorsa (pace, nabız, mesafe)
- comparison: Sadece karşılaştırma isteniyorsa (trend, haftalık değişim)
- activity_ref: Aktivite referansı varsa (son koşu = "last", bu koşu = "this")

ÖNEMLİ: 
- Konuşma geçmişindeki bağlamı kullan
- Emin değilsen confidence düşük ver (0.5-0.7)
- Sadece JSON döndür, başka bir şey yazma

JSON:"""


def get_api_key_from_db():
    """Get API key from database for user 1."""
    try:
        from database import SessionLocal
        from coach.crypto import decrypt_api_key
        import models
        
        db = SessionLocal()
        user = db.query(models.User).filter(models.User.id == 1).first()
        if user and user.gemini_api_key_encrypted:
            api_key = decrypt_api_key(user.gemini_api_key_encrypted, user.gemini_api_key_iv or b'')
            db.close()
            return api_key
        db.close()
    except Exception as e:
        print(f"Failed to get API key from DB: {e}")
    return None


class IntentClassifier:
    """Fast intent classifier using Gemini Flash with JSON output."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_api_key_from_db() or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash-lite")
        else:
            self.model = None
    
    def classify(
        self, 
        message: str, 
        conversation_history: str = "",
        return_debug: bool = False
    ) -> IntentResult:
        """
        Classify user message into a handler type with entities.
        
        Args:
            message: User's message in Turkish
            conversation_history: Formatted conversation history string
            return_debug: If True, return (IntentResult, debug_dict)
            
        Returns:
            IntentResult, or tuple (IntentResult, debug_dict) if return_debug=True
        """
        debug_info = {
            "model": "gemini-2.0-flash-lite",
            "prompt": None,
            "raw_response": None,
            "parsed_json": None,
            "result": None
        }
        
        if not self.model:
            result = self._fallback_classify(message)
            debug_info["model"] = "fallback_regex"
            debug_info["result"] = result.to_dict()
            return (result, debug_info) if return_debug else result
        
        try:
            # Build prompt with conversation history
            history_section = ""
            if conversation_history:
                history_section = f"KONUŞMA GEÇMİŞİ:\n{conversation_history}\n"
            
            prompt = CLASSIFICATION_PROMPT.format(
                message=message,
                conversation_history=history_section
            )
            debug_info["prompt"] = prompt
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=200,
                    temperature=0.0  # Deterministic
                )
            )
            
            raw_response = response.text.strip()
            debug_info["raw_response"] = raw_response
            
            # Parse JSON from response
            result = self._parse_json_response(raw_response)
            debug_info["parsed_json"] = result.to_dict()
            debug_info["result"] = result.to_dict()
            
            return (result, debug_info) if return_debug else result
            
        except Exception as e:
            debug_info["error"] = str(e)
            result = self._fallback_classify(message)
            debug_info["model"] = "fallback_regex"
            debug_info["result"] = result.to_dict()
            return (result, debug_info) if return_debug else result
    
    def _parse_json_response(self, raw_response: str) -> IntentResult:
        """Parse JSON from LLM response."""
        try:
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try raw JSON
                json_str = raw_response
            
            # Clean up common issues
            json_str = json_str.strip()
            if json_str.startswith('{') and json_str.endswith('}'):
                data = json.loads(json_str)
                
                intent = data.get("intent", "sohbet_handler")
                if intent not in VALID_HANDLERS:
                    # Try to match
                    for valid in VALID_HANDLERS:
                        if valid in intent or intent in valid:
                            intent = valid
                            break
                    else:
                        intent = "sohbet_handler"
                
                # Clean entities - remove None/null values
                entities = data.get("entities", {})
                entities = {k: v for k, v in entities.items() if v is not None and v != "null" and v != ""}
                
                confidence = float(data.get("confidence", 0.9))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
                
                return IntentResult(
                    intent=intent,
                    entities=entities,
                    confidence=confidence
                )
        except (json.JSONDecodeError, ValueError) as e:
            pass
        
        # If JSON parsing fails, try to extract handler name
        for handler in VALID_HANDLERS:
            if handler in raw_response.lower():
                return IntentResult(intent=handler, confidence=0.7)
        
        return IntentResult(intent="sohbet_handler", confidence=0.5)
    
    def _fallback_classify(self, message: str) -> IntentResult:
        """Simple regex fallback if API fails."""
        msg = message.lower().strip()
        entities = {}
        
        # Greetings
        if any(g in msg for g in ["selam", "merhaba", "hey", "iyi günler"]):
            return IntentResult("welcome_intent", entities, 0.95)
        
        # Small talk
        if any(s in msg for s in ["nasılsın", "naber", "ne haber", "keyif"]):
            return IntentResult("small_talk_intent", entities, 0.95)
        
        # Farewell
        if any(f in msg for f in ["hoşçakal", "görüşürüz", "bye", "iyi geceler"]):
            return IntentResult("farewell_intent", entities, 0.95)
        
        # Training detail - extract date entities
        if any(t in msg for t in ["son koşu", "son antrenman", "dünkü koşu", "bu koşu"]):
            if "dün" in msg:
                entities["date"] = "yesterday"
            elif "son" in msg:
                entities["activity_ref"] = "last"
            elif "bu" in msg:
                entities["activity_ref"] = "this"
            return IntentResult("training_detail_handler", entities, 0.9)
        
        if any(t in msg for t in ["antrenman", "analiz", "koşumu", "aktivite"]):
            entities["activity_ref"] = "last"
            return IntentResult("training_detail_handler", entities, 0.85)
        
        # DB queries - extract metric entities
        if any(d in msg for d in ["kaç km", "toplam", "ortalama", "trend"]):
            if "km" in msg or "mesafe" in msg:
                entities["metric"] = "distance"
            if "hafta" in msg:
                entities["date"] = "last_week"
            elif "ay" in msg:
                entities["date"] = "last_month"
            return IntentResult("db_handler", entities, 0.9)
        
        if any(d in msg for d in ["hafta", "ay", "karşılaştır"]):
            if "hafta" in msg:
                entities["comparison"] = "weekly"
            elif "ay" in msg:
                entities["comparison"] = "monthly"
            return IntentResult("db_handler", entities, 0.85)
        
        # Default
        return IntentResult("sohbet_handler", entities, 0.7)


# Singleton instance
_classifier = None

def get_classifier() -> IntentClassifier:
    """Get or create the global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(message: str, conversation_history: str = "") -> str:
    """Convenience function for quick classification. Returns handler name only."""
    result = get_classifier().classify(message, conversation_history)
    return result.intent


def classify_intent_with_debug(message: str, conversation_history: str = ""):
    """Classify with debug info. Returns (handler_name, debug_dict) for backward compat."""
    result, debug = get_classifier().classify(message, conversation_history, return_debug=True)
    # Return handler string for backward compatibility
    debug["intent_result"] = result.to_dict()
    return result.intent, debug


def classify_intent_full(message: str, conversation_history: str = "") -> IntentResult:
    """Full classification returning IntentResult object."""
    return get_classifier().classify(message, conversation_history)


def classify_intent_full_with_debug(message: str, conversation_history: str = ""):
    """Full classification with debug. Returns (IntentResult, debug_dict)."""
    return get_classifier().classify(message, conversation_history, return_debug=True)
