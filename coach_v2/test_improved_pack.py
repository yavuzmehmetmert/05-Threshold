"""
Tests for Improved Coach V2 Analysis Pack
=========================================
"""

import unittest
from coach_v2.analysis_pack_builder import AnalysisPackBuilder
from coach_v2.targeted_extraction import TargetedExtractor

class TestImprovedPack(unittest.TestCase):
    
    def setUp(self):
        self.builder = AnalysisPackBuilder()
        self.extractor = TargetedExtractor()
        
        # Mock data with Cardiac Drift (HR rises, Pace steady)
        self.mock_drift_data = {
            'activityName': 'Drift Run',
            'summaryDTO': {
                'distance': 10000.0,
                'duration': 3000.0, 
                'averageSpeed': 3.33,
                'averageHR': 155.0,
                'averageRunningCadenceInStepsPerMinute': 170.0
            },
            'laps': [
                {'duration': 600, 'distance': 2000, 'averageSpeed': 3.33, 'averageHR': 140},
                {'duration': 600, 'distance': 2000, 'averageSpeed': 3.33, 'averageHR': 145},
                {'duration': 600, 'distance': 2000, 'averageSpeed': 3.33, 'averageHR': 160},
                {'duration': 600, 'distance': 2000, 'averageSpeed': 3.33, 'averageHR': 175}, 
            ]
        }

    def test_cardiac_drift_flag(self):
        pack = self.builder.build_pack(self.mock_drift_data)
        flags = pack['flags']
        
        # First half avg HR: (140+145)/2 = 142.5
        # Second half avg HR: (160+175)/2 = 167.5
        # Drift: 167.5 > 142.5 * 1.05 (149.6) -> True
        
        drift_flag = next((f for f in flags if "Cardiac Drift" in f), None)
        self.assertIsNotNone(drift_flag)
        self.assertIn("rose from 142 to 167", drift_flag)

    def test_deep_analysis_extraction(self):
        pack = self.builder.build_pack(self.mock_drift_data)
        context = self.extractor.extract_context(pack, 'activity_analysis')
        
        self.assertIn("# DEEP ANALYSIS CONTEXT", context)
        self.assertIn("# DETAILED SPLITS", context)
        self.assertIn("Cardiac Drift", context) # Should include flags
        self.assertIn("AVG_HR: 155", context)

if __name__ == '__main__':
    unittest.main()
