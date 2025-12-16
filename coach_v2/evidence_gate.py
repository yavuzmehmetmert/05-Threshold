"""
Coach V2 Evidence Gate (Strict)
===============================

Guardrail system to prevent hallucinations.
Ensures that numeric claims in LLM output are supported by the input context.

STRICT MODE:
- Builds a "Safe Number Set" from the input context.
- Rejects any significant number in output that isn't in the Safe Set.
"""

import re
from typing import List, Set, Tuple

class EvidenceGate:
    def __init__(self):
        pass

    def validate(self, llm_output: str, input_context: str) -> Tuple[bool, str]:
        """
        Validate LLM output against input context.
        Returns: (is_valid, violation_reason)
        """
        # Extract number sets
        safe_set = self._extract_numbers(input_context)
        output_tokens = self._extract_numbers(llm_output)
        
        # Check support
        violations = []
        for token in output_tokens:
            if not self._is_supported(token, safe_set):
                violations.append(str(token))
                
        if violations:
            return False, f"Unsupported numbers found: {', '.join(violations[:3])}..."
            
        return True, ""

    def _extract_numbers(self, text: str) -> Set[float]:
        """
        Extract numeric tokens. 
        Handling time formats (5:30) as normalized floats (5.5) or distinct component matching?
        Let's treat "5:30" as string "5:30" extraction check? No, LLM might say "5.5 mins".
        
        Strategy: Extract float matches.
        ALSO extract "MM:SS" patterns and convert to decimal minutes for equivalence checking.
        """
        dataset = set()
        
        # 1. Simple Floats/Ints
        # Regex matches 123, 12.34
        matches = re.findall(r'\b\d+(?:[\.,]\d+)?\b', text)
        for m in matches:
            try:
                val = float(m.replace(',', '.'))
                # Ignore small integers < 5 usually (sets, reps, step 1) unless context implies metric?
                # Actually strict mode says ALL numbers must exist.
                # If output says "Step 1", input better have "1".
                # To be practical, let's ignore year-like numbers 2020-2030 to avoid date confusion if dates aren't fully parsed.
                if 2020 <= val <= 2030: continue
                dataset.add(val)
            except: pass
            
        # 2. Time Patterns (Paces/Durations)
        # Match "5:30", "1:25:00"
        # We store them as decimal minutes in the set for robust comparison
        time_matches = re.findall(r'\b(\d{1,2}):(\d{2})\b', text)
        for mm, ss in time_matches:
            try:
                decimal_min = int(mm) + int(ss)/60.0
                dataset.add(round(decimal_min, 2))
                # Also add the raw components just in case "5 minutes 30 seconds"
                dataset.add(float(mm))
                dataset.add(float(ss))
            except: pass
            
        return dataset

    def _is_supported(self, target: float, safe_set: Set[float], tolerance=0.1) -> bool:
        """Check if target exists in safe set within tolerance."""
        for safe in safe_set:
            if abs(target - safe) < tolerance:
                return True
        return False
