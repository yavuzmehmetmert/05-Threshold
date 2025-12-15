"""
Coach V2 - Memory-aware AI Running Coach
=========================================

A complete rewrite of the AI coach module with:
- Daily learning pipelines (no LLM retraining)
- Bounded context for token efficiency
- Provider-agnostic LLM interface
- RAG knowledge base

Key Design Principles:
1. Backend computes everything - LLM only explains
2. facts_text format for high LLM salience
3. Progressive disclosure - fetch minimal first
4. All summaries bounded (facts <= 600 chars, summary <= 1200 chars)
"""

from coach_v2.repository import CoachV2Repository
from coach_v2.summary_builder import SummaryBuilder
from coach_v2.orchestrator import CoachOrchestrator
from coach_v2.pipeline import DailyPipeline
from coach_v2.llm_client import LLMClient, GeminiClient

__all__ = [
    'CoachV2Repository',
    'SummaryBuilder',
    'CoachOrchestrator',
    'DailyPipeline',
    'LLMClient',
    'GeminiClient',
]
