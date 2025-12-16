"""
Test for Greeting Priority Fix
==============================
"""
import unittest
from coach_v2.query_understanding import parse_user_query, ParsedIntent
from coach_v2.query_understanding import PinnedState
from datetime import date

class TestGreetingPriority(unittest.TestCase):
    
    def test_greeting_with_intent(self):
        """Verify 'Selam intentional_query' executes Intent, not Greeting."""
        # This used to fail because "selam" matched first and returned early
        query = "selam coach son hafta nasıldı sence"
        
        intent = parse_user_query(query)
        print(f"Query: '{query}' -> Intent: {intent.intent_type}")
        
        self.assertEqual(intent.intent_type, 'trend', "Should ignore 'selam' and see 'son hafta'")

    def test_pure_greeting(self):
        """Verify 'Selam' alone works and likely triggers safe greeting."""
        query = "Selam"
        intent = parse_user_query(query)
        self.assertEqual(intent.intent_type, 'greeting')
        
        # Note: We can't test full orchestrator response here easily without mocking LLM, 
        # but the intent logic is the first line of defense.
        pass

if __name__ == '__main__':
    unittest.main()
