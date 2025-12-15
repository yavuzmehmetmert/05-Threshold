"""
Gemini Client for AI Coach
Handles LLM calls with token tracking, caching, and tool support
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import google.generativeai as genai


@dataclass
class TokenUsage:
    """Token usage tracking."""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    
    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class GenerationResult:
    """Result from LLM generation."""
    text: str
    usage: TokenUsage
    tool_calls: List[Dict[str, Any]] = None
    finish_reason: str = "stop"
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class GeminiClient:
    """
    Wrapper for Gemini API with:
    - Cached prefix support
    - Token tracking
    - Tool calling
    """
    
    # Prompt templates directory
    PROMPTS_DIR = Path(__file__).parent / "prompts"
    
    # Estimated tokens per character (rough heuristic)
    CHARS_PER_TOKEN = 3.5
    
    def __init__(self, api_key: str, model: str = "gemini-3-pro-preview"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key
            model: Model to use (default: gemini-3-pro-preview - latest with best reasoning)
        """
        self.api_key = api_key
        self.model_name = model
        
        # Configure API
        genai.configure(api_key=api_key)
        
        # Load cached prefix
        self._cached_prefix = self._load_cached_prefix()
        self._cached_prefix_tokens = self._estimate_tokens(self._cached_prefix)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=self._cached_prefix
        )
    
    def _load_cached_prefix(self) -> str:
        """Load the cached system prompt prefix."""
        prefix_file = self.PROMPTS_DIR / "cached_prefix.txt"
        if prefix_file.exists():
            return prefix_file.read_text(encoding="utf-8")
        return ""
    
    def _load_mode_prompt(self, mode: str) -> str:
        """Load mode-specific prompt."""
        mode_file = self.PROMPTS_DIR / f"{mode}_mode.txt"
        if mode_file.exists():
            return mode_file.read_text(encoding="utf-8")
        return ""
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        if not text:
            return 0
        return int(len(text) / self.CHARS_PER_TOKEN)
    
    def generate(
        self,
        prompt: str,
        mode: str = "chat",
        context: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict]] = None,
        max_output_tokens: int = 1024,
        temperature: float = 0.7
    ) -> GenerationResult:
        """
        Generate response from Gemini.
        
        Args:
            prompt: User message/prompt
            mode: Mode prompt to use (chat, briefing, learn)
            context: Additional context to include
            tools: Tool definitions for function calling
            max_output_tokens: Max tokens in response
            temperature: Generation temperature
            
        Returns:
            GenerationResult with text, usage, and tool calls
        """
        # Build full prompt
        parts = []
        
        # Add mode-specific instructions
        mode_prompt = self._load_mode_prompt(mode)
        if mode_prompt:
            parts.append(mode_prompt)
        
        # Add context if provided - make headers VERY prominent
        if context:
            parts.append("\n# ⚠️ BAĞLAM - BU VERİLER GERÇEK, MUTLAKA KULLAN!")
            
            # Priority order and enhanced headers
            priority_labels = {
                "last_activity": "📊 SON ANTRENMAN DETAYLARI (İNTERVAL/ZONE BİLGİSİ BURADA!)",
                "profile": "👤 KULLANICI PROFİLİ",
                "recent_7d": "📅 SON 7 GÜN ÖZETİ",
                "user_analysis": "🧠 KULLANICI ANALİZİ",
                "correlations": "📈 PERFORMANS KORELASYONLARI",
                "biometrics_7d": "💓 BİYOMETRİK VERİLER",
                "conversation": "💬 ÖNCEKİ KONUŞMA"
            }
            
            for key, value in context.items():
                if value:
                    label = priority_labels.get(key, f"📋 {key}")
                    if hasattr(value, 'to_context_string'):
                        parts.append(f"## {label}\n{value.to_context_string()}")
                    elif isinstance(value, str):
                        parts.append(f"## {label}\n{value}")
                    elif isinstance(value, dict):
                        parts.append(f"## {label}\n{json.dumps(value, ensure_ascii=False)}")
        
        # Add user message
        parts.append(f"\n# KULLANICI MESAJI\n{prompt}")
        
        full_prompt = "\n\n".join(parts)
        
        # Track token usage
        input_tokens = self._cached_prefix_tokens + self._estimate_tokens(full_prompt)
        
        try:
            # Generate response
            generation_config = genai.GenerationConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            # Extract response text safely - Gemini 2.5 Pro format
            response_text = ""
            try:
                # Try direct text attribute first
                if response and hasattr(response, 'text') and response.text:
                    response_text = response.text
                # Fallback: extract from candidates.content.parts
                elif response and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        parts = candidate.content.parts or []
                        text_parts = []
                        for part in parts:
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                        response_text = "\n".join(text_parts)
            except Exception as e:
                # Log error but continue
                print(f"Response text extraction error: {e}")
                response_text = ""
            
            output_tokens = self._estimate_tokens(response_text)
            
            # Check for tool calls (if using function calling)
            tool_calls = []
            if response and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    parts = candidate.content.parts or []
                    for part in parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            tool_calls.append({
                                "name": part.function_call.name,
                                "args": dict(part.function_call.args) if part.function_call.args else {}
                            })
            
            return GenerationResult(
                text=response_text,
                usage=TokenUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=self._cached_prefix_tokens
                ),
                tool_calls=tool_calls,
                finish_reason="stop"
            )
            
        except Exception as e:
            return GenerationResult(
                text=f"Hata: {str(e)}",
                usage=TokenUsage(input_tokens=input_tokens),
                finish_reason="error"
            )
    
    def generate_with_tools(
        self,
        prompt: str,
        mode: str,
        context: Dict[str, Any],
        tool_functions: Dict[str, Callable],
        max_iterations: int = 3
    ) -> GenerationResult:
        """
        Generate response with iterative tool calling.
        
        Args:
            prompt: User message
            mode: Mode prompt to use
            context: Context data
            tool_functions: Dict of tool_name -> callable
            max_iterations: Max tool call iterations
            
        Returns:
            Final GenerationResult after tool execution
        """
        # Build tool definitions for Gemini
        tools = []
        for name, func in tool_functions.items():
            if hasattr(func, '__tool_schema__'):
                tools.append(func.__tool_schema__)
        
        current_context = context.copy()
        total_usage = TokenUsage()
        
        for i in range(max_iterations):
            result = self.generate(
                prompt=prompt,
                mode=mode,
                context=current_context,
                tools=tools if tools else None
            )
            
            total_usage.input_tokens += result.usage.input_tokens
            total_usage.output_tokens += result.usage.output_tokens
            
            # If no tool calls, we're done
            if not result.tool_calls:
                result.usage = total_usage
                return result
            
            # Execute tool calls
            for tool_call in result.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                if tool_name in tool_functions:
                    try:
                        tool_result = tool_functions[tool_name](**tool_args)
                        # Add tool result to context
                        current_context[f"tool_{tool_name}"] = tool_result
                    except Exception as e:
                        current_context[f"tool_{tool_name}_error"] = str(e)
        
        # Final generation after tools
        final_result = self.generate(
            prompt=prompt,
            mode=mode,
            context=current_context
        )
        
        total_usage.input_tokens += final_result.usage.input_tokens
        total_usage.output_tokens += final_result.usage.output_tokens
        final_result.usage = total_usage
        
        return final_result
    
    def estimate_request_tokens(
        self,
        prompt: str,
        mode: str = "chat",
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Estimate tokens for a request WITHOUT making the API call.
        Useful for pre-flight token budget checks.
        """
        total = self._cached_prefix_tokens
        
        mode_prompt = self._load_mode_prompt(mode)
        total += self._estimate_tokens(mode_prompt)
        
        if context:
            for value in context.values():
                if value:
                    if hasattr(value, 'to_context_string'):
                        total += self._estimate_tokens(value.to_context_string())
                    elif isinstance(value, str):
                        total += self._estimate_tokens(value)
        
        total += self._estimate_tokens(prompt)
        
        return total


def create_client_for_user(user_api_key: str) -> GeminiClient:
    """
    Create a GeminiClient for a specific user's API key.
    
    Args:
        user_api_key: Decrypted user API key
        
    Returns:
        Configured GeminiClient
    """
    return GeminiClient(api_key=user_api_key)
