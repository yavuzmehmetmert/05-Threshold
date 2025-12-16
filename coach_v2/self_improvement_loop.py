"""
Coach V2 Self-Improvement Loop
==============================
Simulates complex user scenarios to evaluate and refine Coach V2 intelligence.
"""

from datetime import date, timedelta
from coach_v2.analysis_pack_builder import AnalysisPackBuilder
from coach_v2.targeted_extraction import TargetedExtractor
from coach_v2.evidence_gate import EvidenceGate
from coach_v2.query_understanding import ParsedIntent, PinnedState

# MOCK DATA FOR SCENARIOS
SCENARIOS = {
    "DATA_MISMATCH": {
        "activityName": "Hard Temple Run",
        "summaryDTO": {
            "distance": 10000.0,
            "duration": 3000.0, 
            "averageHR": 185.0, 
            "maxHR": 195.0,
            "averageSpeed": 3.33,
            "calories": 800
        },
        "laps": [],
        "readinessDTO": {"sleepScore": 90} 
    },
    "GREY_ZONE_RUN": {
        "activityName": "Steady State?",
        "summaryDTO": {
            "distance": 8000.0,
            "duration": 2400.0, # 40 mins
            "averageHR": 155.0, # Classic Zone 3 for many
            "maxHR": 190.0,     # 155 is ~81% - borderline grey/tempo
            "averageSpeed": 3.0
        },
        "laps": [],
    },
    "JUNK_MILES": {
        "activityName": "Short Jog",
        "summaryDTO": {
            "distance": 3000.0, # 3km
            "duration": 900.0,  # 15 mins
            "averageHR": 140.0,
            "averageSpeed": 3.3
        },
        "laps": []
    },
    "RISKY_RECOVERY": {
        "activityName": "Sleep Deprived Tempo",
        "summaryDTO": {
            "distance": 10000.0,
            "duration": 3000.0,
            "averageHR": 175.0, # High intensity
            "averageSpeed": 3.33
        },
        "laps": [],
        "readinessDTO": {"sleepScore": 40} # Danger
    },
    "METRONOME_PACE": {
        "activityName": "Marathon Pace",
        "summaryDTO": {
            "distance": 10000.0,
            "duration": 3000.0,
            "averageHR": 160.0,
            "averageSpeed": 3.33
        },
        # Laps with extremely consistent speed (3.33 m/s)
        "laps": [
            {'averageSpeed': 3.33, 'duration': 300},
            {'averageSpeed': 3.32, 'duration': 300},
            {'averageSpeed': 3.34, 'duration': 300},
            {'averageSpeed': 3.33, 'duration': 300},
            {'averageSpeed': 3.33, 'duration': 300}
        ],
        "readinessDTO": {"sleepScore": 85}
    }
}

def run_simulation():
    builder = AnalysisPackBuilder()
    extractor = TargetedExtractor()
    
    results = []
    
    print("--- STARTING SELF-IMPROVEMENT SIMULATION ---\n")
    
    for name, data in SCENARIOS.items():
        print(f"Testing Scenario: {name}")
        
        # 1. Build Pack
        pack = builder.build_pack(data)
        flags = pack.get('flags', [])
        print(f"  -> Generated Flags: {flags}")
        
        # 4. Check specific intelligent insights
        if name == "DATA_MISMATCH":
            if any("Intensity" in f for f in flags): print("  [PASS] Detected Data Mismatch/High Intensity.")
            else: print("  [FAIL] Missed High Intensity insight.")
            
        elif name == "GREY_ZONE_RUN":
            if any("Grey Zone" in f for f in flags): print("  [PASS] Detected Grey Zone.")
            else: print("  [FAIL] Missed Grey Zone.")
            
        elif name == "JUNK_MILES":
            if any("Volume Alert" in f for f in flags): print("  [PASS] Detected Junk Miles/Short Volume.")
            else: print("  [FAIL] Missed Volume Alert.")
            
        elif name == "RISKY_RECOVERY":
            if any("DANGER ZONE" in f for f in flags): print("  [PASS] Detected Risky Recovery (Hard Run on Bad Sleep).")
            else: print("  [FAIL] Missed Recovery Risk.")
            
        elif name == "METRONOME_PACE":
            if any("METRONOME" in f for f in flags): print("  [PASS] Detected Metronome Pacing.")
            else: print("  [FAIL] Missed Metronome Pacing.")
                
        print("-" * 30)

if __name__ == "__main__":
    run_simulation()
