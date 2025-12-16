"""
Test for Context Stickiness and Evidence Gate Fixes
===================================================
"""
import unittest
from coach_v2.query_understanding import parse_user_query, ParsedIntent, PinnedState
from coach_v2.evidence_gate import EvidenceGate
from datetime import date

class TestContextFix(unittest.TestCase):
    
    def test_status_intent_parsing(self):
        """Verify 'durumum +3' triggers trend intent, not default."""
        query = "Ama son durumda durumum +3"
        # Simulate pinned state (Almada run)
        pinned = PinnedState(garmin_activity_id=123, local_start_date=date(2025, 3, 9), activity_name="Almada")
        
        intent = parse_user_query(query, pinned_state=pinned)
        
        print(f"Query: '{query}' -> Intent: {intent.intent_type}")
        self.assertEqual(intent.intent_type, 'trend', "Should be 'trend' intent for status update")

    def test_evidence_gate_user_input(self):
        """Verify Evidence Gate allows numbers from user correction."""
        gate = EvidenceGate()
        
        db_context = "TSB: -23.8"
        user_message = "Ama TSB +3 aslında"
        llm_response = "Anladım, TSB +3 ise durum harika."
        
        # Old behavior (Fail)
        valid_old, _ = gate.validate(llm_response, db_context)
        self.assertFalse(valid_old, "Old gate should reject +3")
        
        # New behavior (Pass with user message included)
        combined_context = db_context + "\n" + user_message
        valid_new, violation = gate.validate(llm_response, combined_context)
        
        print(f"Validation Result: {valid_new}")
        self.assertTrue(valid_new, f"Should accept +3 because user said it. Violation: {violation}")

if __name__ == '__main__':
    unittest.main()
