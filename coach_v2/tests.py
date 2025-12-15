"""
Coach V2 Query Understanding and Retrieval Tests
=================================================

12+ test scenarios as required.
"""

import pytest
from datetime import date
from unittest.mock import Mock, MagicMock

from coach_v2.query_understanding import parse_user_query, ParsedIntent
from coach_v2.candidate_retrieval import (
    ActivityCandidate, Resolution, CandidateRetriever
)


# ==============================================================================
# TEST 1-4: Query Understanding Tests
# ==============================================================================

class TestQueryUnderstanding:
    """Test parse_user_query extracts Turkish dates correctly."""
    
    def test_1_turkish_date_extraction(self):
        """Scenario 1: Extract '9 mart 2025' correctly."""
        intent = parse_user_query("9 mart 2025 tarihindeki koşumu anlat")
        
        assert len(intent.mentioned_dates) == 1
        assert intent.mentioned_dates[0] == date(2025, 3, 9)
        assert intent.intent_type == 'specific_date'
    
    def test_2_slash_date_format(self):
        """Scenario 2: Extract '9/3/2025' format."""
        intent = parse_user_query("9/3/2025 günü ne koştum?")
        
        assert len(intent.mentioned_dates) == 1
        assert intent.mentioned_dates[0] == date(2025, 3, 9)
    
    def test_3_iso_date_format(self):
        """Scenario 3: Extract ISO format '2025-03-09'."""
        intent = parse_user_query("2025-03-09 aktivitesi")
        
        assert len(intent.mentioned_dates) == 1
        assert intent.mentioned_dates[0] == date(2025, 3, 9)
    
    def test_4_last_activity_intent(self):
        """Scenario 4: Detect 'son antrenmanım' intent."""
        intent = parse_user_query("son antrenmanımı anlat")
        
        assert intent.intent_type == 'last_activity'
        assert len(intent.mentioned_dates) == 0
    
    def test_5_greeting_intent(self):
        """Scenario 5: Detect greeting intent."""
        intent = parse_user_query("Selam!")
        
        assert intent.intent_type == 'greeting'
    
    def test_6_trend_intent(self):
        """Scenario 6: Detect trend intent with days."""
        intent = parse_user_query("Son 4 haftada gelişimim nasıl?")
        
        assert intent.intent_type == 'trend'
        assert intent.trend_days == 28  # 4 weeks
    
    def test_7_activity_name_extraction(self):
        """Scenario 7: Extract activity name keyword."""
        intent = parse_user_query("Almada koşusu nasıldı?")
        
        assert 'almada' in intent.activity_name_keywords
    
    def test_8_date_with_name(self):
        """Scenario 8: Extract both date and name."""
        intent = parse_user_query("9 mart 2025 Almada koşusu")
        
        assert intent.intent_type == 'specific_date'
        assert len(intent.mentioned_dates) == 1
        assert intent.mentioned_dates[0] == date(2025, 3, 9)
        assert 'almada' in intent.activity_name_keywords


# ==============================================================================
# TEST 9-12: Candidate Retrieval Tests
# ==============================================================================

class TestCandidateRetrieval:
    """Test candidate retrieval and resolution."""
    
    def test_9_single_candidate_resolves(self):
        """Scenario 9: Single candidate should resolve directly."""
        candidate = ActivityCandidate(
            garmin_activity_id=123,
            activity_name="Almada Koşusu",
            local_start_date=date(2025, 3, 9),
            distance_km=10.2,
            duration_min=56,
            workout_type='easy',
            facts_text="BEGIN_FACTS...",
            summary_text="Almada koşusu özeti"
        )
        
        # Mock retriever
        retriever = Mock()
        resolution = CandidateRetriever.resolve_candidates(
            retriever, [candidate], None
        )
        
        assert resolution.status == 'selected'
        assert resolution.selected.garmin_activity_id == 123
    
    def test_10_multiple_candidates_need_clarification(self):
        """Scenario 10: Multiple candidates should trigger clarification."""
        candidates = [
            ActivityCandidate(
                garmin_activity_id=123,
                activity_name="Almada Koşusu",
                local_start_date=date(2025, 3, 9),
                distance_km=10.2, duration_min=56,
                workout_type='easy', facts_text=None, summary_text=None
            ),
            ActivityCandidate(
                garmin_activity_id=124,
                activity_name="Almada Trail",
                local_start_date=date(2025, 3, 9),
                distance_km=12.8, duration_min=78,
                workout_type='long', facts_text=None, summary_text=None
            ),
        ]
        
        retriever = Mock()
        resolution = CandidateRetriever.resolve_candidates(
            retriever, candidates, None
        )
        
        assert resolution.status == 'needs_clarification'
        assert len(resolution.candidates) == 2
        assert "Almada Koşusu" in resolution.clarification_message
        assert "Almada Trail" in resolution.clarification_message
    
    def test_11_no_candidates_returns_not_found(self):
        """Scenario 11: No candidates should return not_found."""
        retriever = Mock()
        resolution = CandidateRetriever.resolve_candidates(
            retriever, [], None
        )
        
        assert resolution.status == 'not_found'
        assert "bulamadım" in resolution.clarification_message.lower()
    
    def test_12_name_hint_narrows_down(self):
        """Scenario 12: Name hint should narrow multiple candidates."""
        candidates = [
            ActivityCandidate(
                garmin_activity_id=123,
                activity_name="Almada Koşusu",
                local_start_date=date(2025, 3, 9),
                distance_km=10.2, duration_min=56,
                workout_type='easy', facts_text=None, summary_text=None
            ),
            ActivityCandidate(
                garmin_activity_id=124,
                activity_name="Kadıköy Koşusu",
                local_start_date=date(2025, 3, 9),
                distance_km=12.8, duration_min=78,
                workout_type='long', facts_text=None, summary_text=None
            ),
        ]
        
        retriever = Mock()
        resolution = CandidateRetriever.resolve_candidates(
            retriever, candidates, name_hint="almada"
        )
        
        assert resolution.status == 'selected'
        assert resolution.selected.activity_name == "Almada Koşusu"


# ==============================================================================
# ADDITIONAL SCENARIO TESTS
# ==============================================================================

class TestIntegrationScenarios:
    """Integration-level scenario tests."""
    
    def test_13_disambiguation_son_vs_date(self):
        """Scenario 13: 'son antrenmanım' vs '9 mart' should be different."""
        intent_last = parse_user_query("son antrenmanımı anlat")
        intent_date = parse_user_query("9 mart 2025 antrenmanımı anlat")
        
        assert intent_last.intent_type == 'last_activity'
        assert intent_date.intent_type == 'specific_date'
        assert intent_date.mentioned_dates[0] == date(2025, 3, 9)
    
    def test_14_kadikoy_should_not_match_almada(self):
        """Scenario 14: If asked for Almada, should not return Kadıköy."""
        intent = parse_user_query("Almada koşusunu anlat")
        
        # 'kadıköy' should not be in keywords
        assert 'kadıköy' not in intent.activity_name_keywords
        # 'almada' should be in keywords
        assert 'almada' in intent.activity_name_keywords
    
    def test_15_trend_request_parsing(self):
        """Scenario 15: Trend request should extract correct days."""
        intent = parse_user_query("son 2 haftada ne kadar koştum")
        
        assert intent.intent_type == 'trend'
        assert intent.trend_days == 14  # 2 weeks


# ==============================================================================
# RUN TESTS
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
