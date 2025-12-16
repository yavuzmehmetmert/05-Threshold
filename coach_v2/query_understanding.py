"""
Coach V2 Query Understanding (Enhanced)
========================================

Deterministic query parser with pinned state awareness.

Intent Types:
- greeting: Selamlama
- last_activity: Son antrenmanım
- specific_date: Tarih belirtilmiş
- specific_name: İsim belirtilmiş
- activity_analysis: Pinned activity hakkında follow-up (detay, yorumla)
- laps_or_splits: Lap/split sorusu (en hızlı km)
- health_day_status: Sağlık sorusu (uyku, HRV, stres)
- longitudinal_prep: Uzun dönem analiz (3 ay, hazırlık)
- trend: Genel trend (gelişim)
- general: Genel soru

This runs BEFORE any LLM call.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date, timedelta


# Turkish month names
TURKISH_MONTHS = {
    'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4,
    'mayıs': 5, 'haziran': 6, 'temmuz': 7, 'ağustos': 8,
    'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12
}

# Intent patterns
LAST_ACTIVITY_PATTERNS = [
    r'son\s+(?:antren?man|koşu|aktivite|run)',  # antrenman/antreman
    r'son\s+(?:antren?man|koşu)\w*\s+(?:değerlendir|yorumla|incele|analiz|nasıl)',
    r'son\s+(?:antren?man|koşu)\w*\s+(?:ne\s+)?(?:oldu|gitti|geçti)',
    r'dün(?:kü)?\s+(?:antren?man|koşu)',
    r'bugün(?:kü)?\s+(?:antren?man|koşu)',
    r'en\s+son(?:ki)?',
    r'az\s+önce(?:ki)?\s+(?:koşu)?',
    r'biraz\s+önce',
    r'son\s+(?:koştum|koştun|yaptım|yaptığım)',
    r'(?:koşu|antren?man)\w*\s+(?:analiz|değerlendir|yorumla)',
    r'son\s+(?:antren?man|koşu)\w*\s+(?:hakkında|için)',
    r'son\s+(?:antren?man|koşu)\w*\s+detay',
    r'son\s+(?:antren?man|koşu)\w*\s+ne\s+olduğ',  # "ne olduğunu bilmiyor"
]

TREND_PATTERNS = [
    r'son\s+(\d+)\s*(?:hafta|gün|ay)',
    r'gelişim',
    r'ilerleme',
    r'trend',
    r'genel\s+durum',
    # Broaden to capture typos like 'ahfta'
    r'geçen\s+\w+',      # e.g. "geçen hafta", "geçen ahfta", "geçen ay"
    r'geçtiğimiz\s+\w+', # e.g. "geçtiğimiz hafta"
    r'bu\s+hafta',
    r'nasıl\s+geçti',
    r'hafta\s+nasıl',
    r'nasıl\s+gidiyor',
    r'ne\s+durumda',
    r'ne\s+alemde',
]

GREETING_PATTERNS = [
    r'^selam',
    r'^merhaba',
    r'^hey',
    r'^nasılsın',
    r'^iyi\s+günler',
]

# NEW: Activity analysis follow-up patterns
ACTIVITY_ANALYSIS_PATTERNS = [
    r'detay',
    r'yorumla',
    r'o\s+koşu',
    r'o\s+yarış',
    r'bu\s+antrenman',
    r'bu\s+koşu',
    r'onun\s+hakkında',
    r'daha\s+fazla',
]

# NEW: Laps/splits patterns
LAPS_PATTERNS = [
    r'lap',
    r'split',
    r'en\s+hızlı\s+(?:km|tur)',
    r'kilometre\s+(?:bazında|detay)',
    r'tur\s+süreleri',
]

# NEW: Health/day status patterns
HEALTH_PATTERNS = [
    r'uyku',
    r'hrv',
    r'stres',
    r'nasıl\s+uyan',
    r'sabah',
    r'dinlenmi',
    r'recovery',
    r'toparlanma',
    r'o\s+gün(?:kü)?\s+(?:uyku|stres|hrv)',
]

# NEW: Longitudinal prep patterns (uses date as anchor)
LONGITUDINAL_PATTERNS = [
    r'(\d+)\s*ay(?:lık)?\s+(?:hazırlık|süreç|dönem)',
    r'(\d+)\s*hafta(?:lık)?\s+(?:hazırlık|süreç|dönem)',
    r'hazırlık\s+sürecini?\s+yorumla',
    r'o\s+yarışa?\s+(?:özel|hazırlık)',
    # NEW: Catch "3 ayı yorumla", "4 haftayı analiz et"
    r'(\d+)\s*(?:ay|hafta)\w*\s+(?:yorumla|analiz|değerlendir|nasıl)',
]

# NEW: Status/Form patterns (TSB, CTL, etc.)
STATUS_PATTERNS = [
    r'durum',
    r'form',
    r'tsb',
    r'ctl',
    r'atl',
    r'yorgunluk',
    r'hazır\s+mıyım',
    r'hazır\s+değil',
    r'fiziksel',
]

# NEW: Race Strategy patterns
RACE_STRATEGY_PATTERNS = [
    r'yarış\s+stratejisi',
    r'yarış\w*\s+(?:plan|hedef|taktik)',
    r'10k|5k|21k|maraton|half',
    r'pace\s+(?:hedef|öner|ne)',
    r'(?:geçmiş|tüm)\s+yarış',
    r'performans\w*\s+(?:analiz|değerlendir)',
    r'nasıl\s+(?:bir|bi)\s+strateji',
    r'(?:tempo|sprint|bitiriş)\s+(?:öner|hedef)',
]

# NEW: Temporal/Historical query patterns
TEMPORAL_PATTERNS = [
    r'(?:ne\s+zaman|when).+(?:en\s+hızlı|fastest|PR)',  # When was I fastest?
    r'(?:neden|why|niye).+(?:formsuz|yavaş|kötü|düşük)',  # Why was I slow?
    r'(?:nasıl|how).+(?:gelişti|improved|değişti)',  # How did I improve?
    r'(?:karşılaştır|compare|kıyasla)',  # Compare periods
    r'(?:\d+\s+ay\s+önce)',  # X months ago
    r'(?:geçen|önceki)\s+(?:yıl|sezon|dönem)',  # Last year/season
    r'(?:o\s+zaman|o\s+dönem)',  # Back then
    r'(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+ayı?(?:nda)?',  # In month X
    r'beni\s+(?:öğren|tanı|analiz)',  # Learn about me
    r'(?:kim|nasıl\s+bir)\s+(?:koşucu|atlet)',  # What kind of runner am I?
    r'(?:güçlü|zayıf)\s+(?:yan|taraf)',  # Strengths/weaknesses
]

# NEW: Progression/Trend query patterns  
PROGRESSION_PATTERNS = [
    r'(?:ne\s+kadar|how\s+much).+(?:geliş|ilerle)',
    r'(?:ilerle|geliş)(?:me|im|iş)',
    r'(?:form|fitness)\s+(?:değişim|trendi?)',
    r'vo2\s*max',
    r'(?:threshold|eşik)\s+(?:pace|tempo)',
]


@dataclass
class PinnedState:
    """Current pinned activity/date context."""
    garmin_activity_id: Optional[int] = None
    local_start_date: Optional[date] = None
    activity_name: Optional[str] = None
    is_valid: bool = False


@dataclass
class ParsedIntent:
    """Structured intent extracted from user query."""
    
    # What type of query is this?
    intent_type: str
    
    # Extracted date(s)
    mentioned_dates: List[date] = field(default_factory=list)
    
    # Extracted activity name keywords
    activity_name_keywords: List[str] = field(default_factory=list)
    
    # For trend/longitudinal queries
    trend_days: Optional[int] = None
    
    # Original query
    original_query: str = ""
    
    # Confidence score (0-1)
    confidence: float = 0.5
    
    # For longitudinal: anchor date from pinned state
    anchor_date: Optional[date] = None


def parse_user_query(text: str, pinned_state: Optional[PinnedState] = None) -> ParsedIntent:
    """
    Parse user query to extract intent and references.
    
    Args:
        text: User message
        pinned_state: Current pinned activity/date (if any)
    
    This is deterministic - no LLM involved.
    """
    text_lower = text.lower().strip()
    original = text
    
    # 1. Extract dates first (they take priority)
    dates = _extract_dates(text_lower)
    
    # If dates found, this is a date-specific query
    if dates:
        name_keywords = _extract_activity_names(text)
        return ParsedIntent(
            intent_type='specific_date',
            mentioned_dates=dates,
            activity_name_keywords=name_keywords,
            original_query=original,
            confidence=0.85
        )
    
    # 2.5. Check for RACE STRATEGY queries
    for pattern in RACE_STRATEGY_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='race_strategy',
                original_query=original,
                confidence=0.85
            )
    
    # 2.6. Check for TEMPORAL/HISTORICAL queries ("neden şubat'ta formsuzdum?")
    for pattern in TEMPORAL_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='temporal_query',
                original_query=original,
                confidence=0.85
            )
    
    # 2.7. Check for PROGRESSION queries ("VO2max nasıl değişti?")
    for pattern in PROGRESSION_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='progression_query',
                original_query=original,
                confidence=0.85
            )
    
    # 3. Check for HEALTH queries (uses pinned date if available)
    for pattern in HEALTH_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='health_day_status',
                anchor_date=pinned_state.local_start_date if pinned_state and pinned_state.is_valid else None,
                original_query=original,
                confidence=0.85
            )
    
    # 4. Check for LAPS/SPLITS queries (uses pinned activity if available)
    for pattern in LAPS_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='laps_or_splits',
                anchor_date=pinned_state.local_start_date if pinned_state and pinned_state.is_valid else None,
                original_query=original,
                confidence=0.85
            )
    
    # 5. Check for LONGITUDINAL queries (3 ay hazırlık, etc.)
    for pattern in LONGITUDINAL_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            # Calculate days from months/weeks
            days = 90  # default 3 months
            if match.groups():
                try:
                    num = int(match.group(1))
                    if 'ay' in text_lower:
                        days = num * 30
                    elif 'hafta' in text_lower:
                        days = num * 7
                except:
                    pass
            return ParsedIntent(
                intent_type='longitudinal_prep',
                trend_days=days,
                anchor_date=pinned_state.local_start_date if pinned_state and pinned_state.is_valid else None,
                original_query=original,
                confidence=0.8
            )
    
    # 6. Check for ACTIVITY ANALYSIS follow-up (detay, yorumla)
    for pattern in ACTIVITY_ANALYSIS_PATTERNS:
        if re.search(pattern, text_lower):
            # If we have a pinned activity, use it
            if pinned_state and pinned_state.is_valid:
                return ParsedIntent(
                    intent_type='activity_analysis',
                    anchor_date=pinned_state.local_start_date,
                    original_query=original,
                    confidence=0.85
                )
    
    # 7. Check for STATUS/FORM queries (TSB, Form, Durum)
    for pattern in STATUS_PATTERNS:
        if re.search(pattern, text_lower):
             return ParsedIntent(
                intent_type='trend',
                trend_days=28, # Standard lookback for form/ACWR
                anchor_date=pinned_state.local_start_date if pinned_state and pinned_state.is_valid else None,
                original_query=original,
                confidence=0.85
             )

    # 8. Check for trend/general longitudinal
    for pattern in TREND_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            days = 28  # default
            if match.groups():
                try:
                    num = int(match.group(1))
                    if 'hafta' in text_lower:
                        days = num * 7
                    elif 'ay' in text_lower:
                        days = num * 30
                    else:
                        days = num
                except:
                    pass
            return ParsedIntent(
                intent_type='trend',
                trend_days=days,
                original_query=original,
                confidence=0.8
            )
    
    # 8. Check for last activity intent
    for pattern in LAST_ACTIVITY_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='last_activity',
                original_query=original,
                confidence=0.9
            )
    
    # 9. Extract activity name keywords
    name_keywords = _extract_activity_names(text)
    if name_keywords:
        return ParsedIntent(
            intent_type='specific_name',
            activity_name_keywords=name_keywords,
            original_query=original,
            confidence=0.7
        )
    
    # 10. If we have a pinned state and user is asking a follow-up, use it
    if pinned_state and pinned_state.is_valid:
        # Generic follow-up - use pinned activity
        return ParsedIntent(
            intent_type='activity_analysis',
            anchor_date=pinned_state.local_start_date,
            original_query=original,
            confidence=0.6
        )
    
    # 11. Check for greeting (LOWEST PRIORITY - only if nothing else matches)
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, text_lower):
            return ParsedIntent(
                intent_type='greeting',
                original_query=original,
                confidence=0.9
            )

    # Default: general question
    return ParsedIntent(
        intent_type='general',
        original_query=original,
        confidence=0.5
    )


def _extract_dates(text: str) -> List[date]:
    """Extract dates from Turkish text."""
    dates = []
    text_lower = text.lower()
    
    # Pattern 1: "9 mart 2025" or "9 mart" (assume current year if missing)
    pattern1 = r'(\d{1,2})\s+(' + '|'.join(TURKISH_MONTHS.keys()) + r')(?:\s+(\d{4}))?'
    for match in re.finditer(pattern1, text_lower):
        day = int(match.group(1))
        month = TURKISH_MONTHS[match.group(2)]
        year = int(match.group(3)) if match.group(3) else date.today().year
        try:
            dates.append(date(year, month, day))
        except ValueError:
            pass
    
    # Pattern 2: "9/3/2025" or "09-03-2025"
    pattern2 = r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})'
    for match in re.finditer(pattern2, text_lower):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        try:
            dates.append(date(year, month, day))
        except ValueError:
            pass
    
    # Pattern 3: "2025-03-09" (ISO format)
    pattern3 = r'(\d{4})-(\d{2})-(\d{2})'
    for match in re.finditer(pattern3, text_lower):
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            dates.append(date(year, month, day))
        except ValueError:
            pass
    
    return list(set(dates))  # Remove duplicates


def _extract_activity_names(text: str) -> List[str]:
    """Extract potential activity name keywords."""
    keywords = []
    
    # Common location patterns in activity names
    location_patterns = [
        r'(kadıköy|almada|maltepe|bağdat|caddesi|sahil|park|orman)',
        r'(\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+(?:koşu|run|trail))',
    ]
    
    text_lower = text.lower()
    
    for pattern in location_patterns:
        for match in re.finditer(pattern, text_lower):
            keyword = match.group(1)
            if keyword and len(keyword) > 2:
                keywords.append(keyword)
    
    # Also look for quoted names
    quoted = re.findall(r'"([^"]+)"', text)
    keywords.extend(quoted)
    
    return list(set(keywords))
