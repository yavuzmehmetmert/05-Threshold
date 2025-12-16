"""
Tests for Coach V2 Analysis Pack & Extraction
=============================================
"""

import unittest
from datetime import date
from coach_v2.analysis_pack_builder import AnalysisPackBuilder
from coach_v2.targeted_extraction import TargetedExtractor
from coach_v2.evidence_gate import EvidenceGate

class TestAnalysisPack(unittest.TestCase):
    
    def setUp(self):
        self.builder = AnalysisPackBuilder()
        self.extractor = TargetedExtractor()
        self.gate = EvidenceGate()
        self.mock_details = {
            'activityName': 'Morning Run',
            'startTimeLocal': '2025-03-09T08:00:00',
            'summaryDTO': {
                'distance': 5000.0,
                'duration': 1500.0, # 25 mins
                'averageSpeed': 3.33, # ~5:00/km
                'averageHR': 150.0,
                'averageRunningCadenceInStepsPerMinute': 170.0
            },
            'laps': [
                {'duration': 300, 'distance': 1000, 'averageSpeed': 3.33, 'averageHR': 145},
                {'duration': 295, 'distance': 1000, 'averageSpeed': 3.39, 'averageHR': 148},
            ],
            'readinessDTO': {
                'sleepScore': 85,
                'sleepDurationSeconds': 27000, # 7.5 hrs
                'hrvLastNightAvg': 42
            }
        }

    def test_pack_building(self):
        pack = self.builder.build_pack(self.mock_details)
        self.assertIn("DISTANCE: 5.00 km", pack['facts'])
        self.assertIn("AVG_HR: 150", pack['facts'])
        self.assertIn("SLEEP_SCORE: 85", pack['readiness'])
        self.assertIn("| 1 | 0:05:00 | 1.00 | 5:00 | 145 | - |", pack['tables'])

    def test_targeted_extraction_health(self):
        pack = self.builder.build_pack(self.mock_details)
        snippet = self.extractor.extract_context(pack, 'health_day_status')
        self.assertIn("# READINESS & HEALTH", snippet)
        self.assertIn("SLEEP_DURATION: 7.5 hours", snippet)
        # Should NOT contain laps table in health context
        self.assertNotIn("| 1 |", snippet) 

    def test_targeted_extraction_laps(self):
        pack = self.builder.build_pack(self.mock_details)
        snippet = self.extractor.extract_context(pack, 'laps_or_splits')
        self.assertIn("# LAPS & SPLITS", snippet)
        self.assertIn("| 1 |", snippet)
        # Should contain identity
        self.assertIn("ACTIVITY_NAME: Morning Run", snippet)

    def test_evidence_gate(self):
        context = "Average Pace: 5:00/km. HR: 150 bpm."
        
        # Valid
        valid, msg = self.gate.validate("Pace was 5:00/km which is good.", context)
        self.assertTrue(valid)
        
        # Invalid (Hallucination)
        valid, msg = self.gate.validate("Your max HR was 190 bpm.", context)
        self.assertFalse(valid)
        self.assertIn("190", msg)

if __name__ == '__main__':
    unittest.main()
