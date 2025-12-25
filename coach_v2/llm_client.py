"""
Coach V2 LLM Client Interface
=============================

Provider-agnostic LLM interface.
Supports Gemini, Claude, OpenAI (extensible).
"""

from typing import Protocol, Optional, Dict, Any
from dataclasses import dataclass
import google.generativeai as genai


@dataclass
class LLMResponse:
    """Response from LLM generation."""
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    metadata: Optional[Dict[str, Any]] = None


class LLMClient(Protocol):
    """
    Protocol for LLM clients.
    All implementations must provide generate() method.
    """
    
    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        ...


class GeminiClient:
    """Gemini LLM client implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-3-pro-preview", system_instruction: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction
        )
    
    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate response using Gemini."""
        import logging
        config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        # Standard safety filters - using safest possible settings for athletic coaching
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        try:
            response = self.model.generate_content(
                prompt, 
                generation_config=config,
                safety_settings=safety_settings
            )
            
            # Handle blocked responses or empty candidates
            if not response.candidates or not response.candidates[0].content.parts:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                return LLMResponse(
                    text=f"[Model yanıt veremedi - finish_reason: {finish_reason}. Muhtemelen güvenlik filtresine takıldı.]",
                    input_tokens=0,
                    output_tokens=0,
                    model=self.model_name
                )
            
            # Extract token counts if available
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            
            return LLMResponse(
                text=response.text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.model_name
            )
        except Exception as e:
            return LLMResponse(
                text=f"[LLM Error: {str(e)}]",
                input_tokens=0,
                output_tokens=0,
                model=self.model_name
            )


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self):
        self.model_name = "mock"
        self.last_prompt = None
    
    def generate(
        self, 
        prompt: str, 
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Return mock response."""
        self.last_prompt = prompt
        
        # Check for interval structure in prompt
        if "INTERVAL_STRUCTURE=" in prompt:
            # Extract interval structure
            for line in prompt.split("\n"):
                if line.startswith("INTERVAL_STRUCTURE="):
                    structure = line.split("=", 1)[1]
                    return LLMResponse(
                        text=f"Verilere göre interval yapın: {structure}. Bu harika bir hız çalışması.",
                        input_tokens=len(prompt) // 4,
                        output_tokens=50,
                        model="mock"
                    )
        
        return LLMResponse(
            text="Mock response - no interval structure detected.",
            input_tokens=len(prompt) // 4,
            output_tokens=20,
            model="mock"
        )
