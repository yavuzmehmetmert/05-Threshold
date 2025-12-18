# Coach Module Documentation

AI-powered running coach with natural language understanding and personalized analysis.

## Table of Contents

1. [Architecture Overview](./architecture.md)
2. [Request Flow](./request-flow.md)
3. [Intent Classification](./intent-classification.md)
4. [Handlers](./handlers.md)
5. [SQL Agent](./sql-agent.md)
6. [LLM Configuration](./llm-config.md)

## Quick Start

```python
from coach_v2.orchestrator import CoachOrchestrator, ChatRequest
from coach_v2.llm_client import GeminiClient

# Initialize
llm = GeminiClient(api_key="...")
coach = CoachOrchestrator(db_session, llm)

# Chat
request = ChatRequest(user_id=1, message="Son koşumu analiz et")
response = coach.handle_chat(request)
print(response.message)
```

## Key Features

- **AI Intent Classification**: Gemini Flash for fast intent detection
- **Multi-Handler Routing**: Static responses, LLM conversations, SQL queries
- **Tedesco Communication Style**: Direct, thoughtful, no unnecessary questions
- **Full Debug Support**: Step-by-step visibility into the pipeline
