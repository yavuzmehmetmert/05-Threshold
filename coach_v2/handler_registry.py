"""
Handler Registry
==================

Central registry of all available handlers and their capabilities.
Used by Planner to understand what tools are available.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class HandlerCapability:
    """Describes what a handler can do."""
    name: str
    description: str
    use_when: List[str]  # Keywords/conditions when to use
    provides: List[str]  # What data this handler provides
    requires: List[str] = field(default_factory=list)  # Required entities
    can_chain: bool = True  # Can be chained with other handlers
    is_static: bool = False  # Static response (no LLM)
    

# Central registry of all handlers
HANDLER_REGISTRY: Dict[str, HandlerCapability] = {
    
    # ========== STATIC HANDLERS ==========
    "welcome_intent": HandlerCapability(
        name="welcome_intent",
        description="Selamlama cevabı verir",
        use_when=["selam", "merhaba", "hey", "iyi günler", "günaydın"],
        provides=["greeting"],
        can_chain=False,
        is_static=True
    ),
    
    "small_talk_intent": HandlerCapability(
        name="small_talk_intent",
        description="Hal hatır sorar, nasılsın cevabı",
        use_when=["nasılsın", "naber", "ne haber", "keyifler", "iyi misin"],
        provides=["small_talk"],
        can_chain=False,
        is_static=True
    ),
    
    "farewell_intent": HandlerCapability(
        name="farewell_intent",
        description="Vedalaşma cevabı verir",
        use_when=["hoşçakal", "görüşürüz", "bye", "iyi geceler"],
        provides=["farewell"],
        can_chain=False,
        is_static=True
    ),
    
    # ========== DATA HANDLERS ==========
    "training_detail_handler": HandlerCapability(
        name="training_detail_handler",
        description="Spesifik aktivite/koşu analizi yapar. HRV, uyku, stres, hava durumu, irtifa dahil.",
        use_when=[
            "koşumu analiz et", "son koşu", "bugünkü koşu", "dünkü koşu",
            "antrenmanı analiz", "karşılaştır", "nasıl koştum", "performansım"
        ],
        provides=[
            "activity_metrics",  # pace, distance, duration, hr, cadence
            "hrv_data",          # HRV from previous night
            "sleep_data",        # Sleep score, duration, deep sleep
            "stress_data",       # Stress levels
            "weather_data",      # Temperature, humidity, wind
            "altitude_data",     # Elevation, GPS altitude
            "training_load",     # CTL, ATL, TSB
            "lap_data"           # Lap splits for analysis
        ],
        requires=["activity_ref"],  # which activity: last, today, yesterday, specific
        can_chain=True
    ),
    
    "db_handler": HandlerCapability(
        name="db_handler",
        description="Veritabanından TOPLAM istatistik çeker. Haftalık/aylık toplamlar, ortalamalar.",
        use_when=[
            "kaç km", "toplam mesafe", "haftalık", "aylık", "ortalama pace",
            "toplam süre", "kaç antrenman", "en hızlı", "en uzun"
        ],
        provides=[
            "aggregate_stats",   # totals, averages
            "trends",            # weekly/monthly trends
            "records"            # personal bests
        ],
        requires=["date", "metric"],  # time period and what to measure
        can_chain=True
    ),
    
    # ========== MEMORY HANDLER ==========
    "memory_handler": HandlerCapability(
        name="memory_handler",
        description="Kullanıcının paylaştığı bilgiyi kaydeder (uyku notu, sakatlık, alkol, vb.)",
        use_when=[
            "alkol aldım", "iyi uyuyamadım", "sakatlandım", "grip oldum",
            "stresliydim", "yarış var", "hedefim"
        ],
        provides=["user_context"],
        requires=["save_type", "save_content"],
        can_chain=True
    ),
    
    # ========== LLM HANDLER ==========
    "sohbet_handler": HandlerCapability(
        name="sohbet_handler",
        description="Genel sohbet, tavsiye, verileri yorumlama. Genelde son adım olarak kullanılır.",
        use_when=[
            "tavsiye", "ne yapmalıyım", "yorum", "açıkla", "öner",
            "düşüncen", "yarın ne yapayım"
        ],
        provides=[
            "advice",            # coaching advice
            "interpretation",    # data interpretation
            "recommendations"    # what to do next
        ],
        can_chain=True  # Usually the final step
    ),
    
    # ========== INPUT HANDLER ==========
    "ask_user_handler": HandlerCapability(
        name="ask_user_handler",
        description="Kullanıcıdan ek bilgi ister (uyku, yaşam tarzı, hedef)",
        use_when=[
            "HRV düşük", "performans düştü", "anormal veri", "bağlam lazım"
        ],
        provides=["user_input"],
        requires=["question"],
        can_chain=True
    ),
}


def get_handler_capabilities_prompt() -> str:
    """Generate dynamic prompt section for Planner about available handlers."""
    lines = ["MEVCUT HANDLER'LAR VE YETENEKLERİ:"]
    lines.append("")
    
    for name, cap in HANDLER_REGISTRY.items():
        lines.append(f"### {name}")
        lines.append(f"Açıklama: {cap.description}")
        lines.append(f"Ne zaman kullan: {', '.join(cap.use_when[:5])}")
        lines.append(f"Sağladığı veri: {', '.join(cap.provides)}")
        if cap.requires:
            lines.append(f"Gereken entity: {', '.join(cap.requires)}")
        if cap.is_static:
            lines.append("⚡ Statik cevap (tek başına kullan)")
        if not cap.can_chain:
            lines.append("🔒 Zincirleme yapılamaz")
        lines.append("")
    
    return "\n".join(lines)


def get_handler_by_name(name: str) -> HandlerCapability:
    """Get handler capability by name."""
    return HANDLER_REGISTRY.get(name)


def get_data_handlers() -> List[str]:
    """Get list of handlers that provide data."""
    return [
        name for name, cap in HANDLER_REGISTRY.items()
        if cap.can_chain and not cap.is_static
    ]
