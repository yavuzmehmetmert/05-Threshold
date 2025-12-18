"""
AI Intent Classifier
=====================

Uses Gemini Flash for fast intent classification.
Returns only the handler name, nothing else.
"""

import os
import google.generativeai as genai
from typing import Literal

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

# Minimal classification prompt
CLASSIFICATION_PROMPT = """Koşucu mesajı: "{message}"

Sadece şu handler isimlerinden BİRİNİ yaz, başka hiçbir şey yazma:
- welcome_intent (selam, merhaba, hey, iyi günler)
- small_talk_intent (nasılsın, naber, keyifler nasıl, ne haber)
- farewell_intent (hoşçakal, görüşürüz, bye, iyi geceler)
- sohbet_handler (genel sohbet, tavsiye, soru-cevap, koşu hakkında bilgi)
- db_handler (istatistik, trend, karşılaştırma, kaç km, ortalama, en hızlı, toplam)
- training_detail_handler (son koşu, antrenman analizi, bu koşu, dünkü koşu, son aktivite, koşumu analiz et)

Handler:"""


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
    """Fast intent classifier using Gemini Flash."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_api_key_from_db() or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use fastest available model
            self.model = genai.GenerativeModel("gemini-2.0-flash-lite")
        else:
            self.model = None
    
    def classify(self, message: str, return_debug: bool = False):
        """
        Classify user message into a handler type.
        
        Args:
            message: User's message in Turkish
            return_debug: If True, return (handler, debug_dict)
            
        Returns:
            Handler type string, or tuple (handler, debug_dict) if return_debug=True
        """
        debug_info = {
            "model": "gemini-2.0-flash-lite",
            "prompt": None,
            "raw_response": None,
            "handler": None
        }
        
        if not self.model:
            handler = self._fallback_classify(message)
            debug_info["model"] = "fallback_regex"
            debug_info["handler"] = handler
            return (handler, debug_info) if return_debug else handler
        
        try:
            prompt = CLASSIFICATION_PROMPT.format(message=message)
            debug_info["prompt"] = prompt
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=20,
                    temperature=0.0  # Deterministic
                )
            )
            
            raw_response = response.text.strip()
            debug_info["raw_response"] = raw_response
            
            # Extract and validate handler name
            handler = raw_response.lower()
            
            # Clean up potential formatting
            handler = handler.replace("handler:", "").strip()
            handler = handler.split()[0] if handler.split() else handler
            
            if handler in VALID_HANDLERS:
                debug_info["handler"] = handler
                return (handler, debug_info) if return_debug else handler
            
            # Try to match partial
            for valid in VALID_HANDLERS:
                if valid in handler or handler in valid:
                    debug_info["handler"] = valid
                    return (valid, debug_info) if return_debug else valid
            
            # Default fallback
            debug_info["handler"] = "sohbet_handler"
            return ("sohbet_handler", debug_info) if return_debug else "sohbet_handler"
            
        except Exception as e:
            debug_info["error"] = str(e)
            handler = self._fallback_classify(message)
            debug_info["handler"] = handler
            debug_info["model"] = "fallback_regex"
            return (handler, debug_info) if return_debug else handler
    
    def _fallback_classify(self, message: str) -> HandlerType:
        """Simple regex fallback if API fails."""
        msg = message.lower().strip()
        
        # Greetings
        if any(g in msg for g in ["selam", "merhaba", "hey", "iyi günler"]):
            return "welcome_intent"
        
        # Small talk
        if any(s in msg for s in ["nasılsın", "naber", "ne haber", "keyif"]):
            return "small_talk_intent"
        
        # Farewell
        if any(f in msg for f in ["hoşçakal", "görüşürüz", "bye", "iyi geceler"]):
            return "farewell_intent"
        
        # Training detail
        if any(t in msg for t in ["son koşu", "antrenman", "analiz", "koşumu", "dünkü", "aktivite"]):
            return "training_detail_handler"
        
        # DB queries
        if any(d in msg for d in ["kaç km", "toplam", "ortalama", "trend", "hafta", "ay"]):
            return "db_handler"
        
        # Default
        return "sohbet_handler"


# Singleton instance
_classifier = None

def get_classifier() -> IntentClassifier:
    """Get or create the global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(message: str) -> HandlerType:
    """Convenience function for quick classification."""
    return get_classifier().classify(message)


def classify_intent_with_debug(message: str):
    """Classify with debug info. Returns (handler, debug_dict)."""
    return get_classifier().classify(message, return_debug=True)
