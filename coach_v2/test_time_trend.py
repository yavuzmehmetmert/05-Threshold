"""
Test for Time-Based Trend Detection
===================================
"""
import unittest
from coach_v2.query_understanding import parse_user_query, ParsedIntent, PinnedState
from datetime import date

class TestTimeTrend(unittest.TestCase):
    
    def test_last_week_intent(self):
        """Verify 'geçtiğimiz hafta' triggers trend intent."""
        # Queries that failed before (including typo)
        queries = [
            "Nasıldı geçtiğimiz hafta",
            "Geçen hafta nasıl geçti",
            "Bu hafta durum ne",
            "Hafta nasıl gidiyor",
            "Nasıldı geçtiğimiz ahfta" # The user's exact typo
        ]
        
        # Simulate pinned state (Almada run) - strict test: verify we DON'T use it
        pinned = PinnedState(garmin_activity_id=123, local_start_date=date(2025, 3, 9), activity_name="Almada")
        
        for q in queries:
            intent = parse_user_query(q, pinned_state=pinned)
            print(f"Query: '{q}' -> Intent: {intent.intent_type}")
            self.assertEqual(intent.intent_type, 'trend', f"Query '{q}' should be trend")
            self.assertEqual(intent.trend_days, 28, "Default trend lookback applied")

if __name__ == '__main__':
    unittest.main()
