"""
Coach V2 Targeted Extraction
============================

Extracts strictly bounded context snippets from the Analysis Pack based on user intent.
This ensures the LLM sees ONLY relevant data, saving tokens and reducing hallucinations.

Logic:
- LAPS/SPLITS -> Table A + Table B (Technique) + Facts
- READINESS -> Readiness Section + Facts (Identity only)
- TECHNIQUE -> Table B + Flags + Facts (Technical)
- DEFAULT -> Facts + Flags + Readiness (Summary)
"""

from typing import Dict, Any

class TargetedExtractor:
    def __init__(self):
        pass

    def extract_context(self, analysis_pack: Dict[str, Any], intent_type: str) -> str:
        """
        Extract relevant context snippet.
        
        Args:
            analysis_pack: Full pack from AnalysisPackBuilder
            intent_type: ParsedIntent.intent_type
        
        Returns:
            Bounded context string.
        """
        facts = analysis_pack.get('facts', '')
        tables = analysis_pack.get('tables', '')
        flags = "\n".join(analysis_pack.get('flags', []))
        readiness = analysis_pack.get('readiness', '')
        
        context_parts = []
        
        # 1. Base Context (Identity)
        # Always good to know what activity we are talking about
        identity_lines = [line for line in facts.split('\n') if any(x in line for x in ['ACTIVITY_NAME', 'type', 'DATE'])]
        context_parts.append("\n".join(identity_lines))
        
        # 2. Specifics based on Intent
        if intent_type == 'laps_or_splits':
            context_parts.append("# LAPS & SPLITS")
            context_parts.append(tables)
            context_parts.append("# FLAGS")
            context_parts.append(flags)
            
        elif intent_type == 'health_day_status':
            context_parts.append("# READINESS & HEALTH")
            context_parts.append(readiness)
            
        elif intent_type == 'technique': # If we support this specific intent
            context_parts.append("# TECHNIQUE METRICS")
            # Filter facts for cadence, gct, vo
            tech_facts = [line for line in facts.split('\n') if any(x in line for x in ['CADENCE', 'GCT', 'OSC', 'STRIDE', 'POWER'])]
            context_parts.append("\n".join(tech_facts))
            context_parts.append(tables) # Table often has technique
            context_parts.append(flags)
            
        elif intent_type == 'activity_analysis': # General deep dive
            context_parts.append("# DEEP ANALYSIS CONTEXT")
            context_parts.append(facts)
            context_parts.append("\n# DETAILED SPLITS & METRICS")
            context_parts.append(tables)
            context_parts.append("\n# COACHING FLAGS (Issues/Patterns)")
            context_parts.append(flags)
            context_parts.append("\n# READINESS & RECOVERY")
            context_parts.append(readiness) # Critical for Elite Context
            
        else:
            # Default fallback (lightweight)
            context_parts.append("# ACTIVITY SUMMARY")
            context_parts.append(facts)
            context_parts.append("# FLAGS")
            context_parts.append(flags)
            
        return "\n\n".join(context_parts)
