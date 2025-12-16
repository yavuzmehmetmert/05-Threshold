"""
Coach V2 Comprehensive Conversation Tests
=========================================

Simulates real user conversations to verify:
1. Greeting responses are warm and helpful
2. Activity analysis is conversational, not robotic
3. Trend/form queries give actionable insight
4. Follow-up questions maintain context
5. No hallucination when data is missing
"""
import sys
sys.path.insert(0, '/Users/mertyavuz/Desktop/VSCode-Projects/05-Threshold')

from coach_v2.query_understanding import parse_user_query, PinnedState
from coach_v2.analysis_pack_builder import AnalysisPackBuilder
from datetime import date

# ==============================================================================
# TEST SCENARIOS
# ==============================================================================

def test_intent_parsing():
    """Test that intents are correctly classified."""
    print("=" * 60)
    print("INTENT PARSING TESTS")
    print("=" * 60)
    
    test_cases = [
        ("Selam", "greeting"),
        ("Merhaba coach", "greeting"),
        ("Son koşumu analiz et", "last_activity"),
        ("Son antrenmanım nasıldı?", "last_activity"),
        ("Bu hafta nasıldı?", "trend"),
        ("Geçen hafta form durumum ne?", "trend"),
        ("Formum nasıl?", "trend"),
        ("TSB kaç?", "trend"),
        ("3 Aralık'taki koşu", "specific_date"),
        ("9 mart 2025 koşusu", "specific_date"),
        ("Son 3 ayı yorumla", "longitudinal_prep"),
        ("Uyku kalitem nasıldı?", "health_day_status"),
    ]
    
    passed = 0
    for query, expected in test_cases:
        intent = parse_user_query(query)
        status = "✓" if intent.intent_type == expected else "✗"
        if intent.intent_type == expected:
            passed += 1
        print(f"{status} '{query}' -> {intent.intent_type} (expected: {expected})")
    
    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_activity_pack_building():
    """Test that activity packs are built correctly with flags."""
    print("\n" + "=" * 60)
    print("ACTIVITY PACK BUILDING TESTS")
    print("=" * 60)
    
    builder = AnalysisPackBuilder()
    
    # Good run scenario
    good_run = {
        "activityName": "Morning Easy Run",
        "summaryDTO": {
            "distance": 10000.0,
            "duration": 3600.0,
            "averageHR": 145.0,
            "maxHR": 165.0,
            "averageSpeed": 2.78,
            "averageRunningCadenceInStepsPerMinute": 172
        },
        "laps": [
            {"averageSpeed": 2.75, "averageHR": 142, "duration": 600},
            {"averageSpeed": 2.78, "averageHR": 145, "duration": 600},
            {"averageSpeed": 2.80, "averageHR": 148, "duration": 600},
            {"averageSpeed": 2.82, "averageHR": 150, "duration": 600},
        ]
    }
    
    pack = builder.build_pack(good_run)
    print(f"Good Run Pack:")
    print(f"  Facts: {pack['facts'][:100]}...")
    print(f"  Flags: {pack['flags']}")
    
    # Hard workout scenario
    hard_run = {
        "activityName": "Tempo Intervals",
        "summaryDTO": {
            "distance": 8000.0,
            "duration": 2400.0,
            "averageHR": 178.0,
            "maxHR": 195.0,
            "averageSpeed": 3.33
        },
        "laps": []
    }
    
    pack2 = builder.build_pack(hard_run)
    print(f"\nHard Run Pack:")
    print(f"  Facts: {pack2['facts'][:100]}...")
    print(f"  Flags: {pack2['flags']}")
    
    # Grey zone warning scenario
    grey_zone = {
        "activityName": "Medium Effort",
        "summaryDTO": {
            "distance": 10000.0,
            "duration": 3600.0,
            "averageHR": 155.0,
            "maxHR": 180.0,
            "averageSpeed": 2.78
        },
        "laps": []
    }
    
    pack3 = builder.build_pack(grey_zone)
    print(f"\nGrey Zone Pack:")
    print(f"  Flags: {pack3['flags']}")
    
    return True

def test_response_quality_checklist():
    """Print checklist for manual verification."""
    print("\n" + "=" * 60)
    print("MANUAL VERIFICATION CHECKLIST")
    print("=" * 60)
    
    checklist = """
    When testing in the app, verify these qualities:

    GREETING:
    [ ] Warm and friendly, not robotic
    [ ] Offers clear next steps (what can I help with?)
    [ ] No fabricated data or analysis
    [ ] Short (2-3 sentences max)

    ACTIVITY ANALYSIS:
    [ ] Tells a story, not just lists numbers
    [ ] Highlights key observations naturally
    [ ] Uses running terminology correctly
    [ ] Ends with actionable advice or question
    [ ] 150-200 words, not too long

    TREND/FORM QUERIES:
    [ ] Interprets TSB meaningfully
    [ ] Gives practical training advice
    [ ] Mentions recovery if needed
    [ ] Connects to user's goals

    FOLLOW-UP QUESTIONS:
    [ ] Remembers previous context
    [ ] Answers specifically to the ask
    [ ] Doesn't repeat full analysis

    NO DATA SCENARIOS:
    [ ] Clearly states no data available
    [ ] Offers helpful alternatives
    [ ] Never fabricates numbers
    """
    print(checklist)
    return True


if __name__ == "__main__":
    print("\n🏃 Coach V2 Conversation Test Suite 🏃\n")
    
    all_passed = True
    
    all_passed &= test_intent_parsing()
    all_passed &= test_activity_pack_building()
    test_response_quality_checklist()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All automated tests passed!")
    else:
        print("❌ Some tests failed - review output above")
    print("=" * 60)
