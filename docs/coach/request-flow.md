# Request Flow

## Overview

Every user message follows the same initial path, then branches based on AI classification.

## Sequence Diagram: Complete Request Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as /api/coach/chat
    participant O as Orchestrator
    participant IC as IntentClassifier
    participant Flash as Gemini Flash
    participant H as Handler
    participant LLM as Gemini Pro
    participant DB as PostgreSQL

    U->>F: Types message
    F->>API: POST /chat {message, user_id}
    API->>O: handle_chat(request)
    
    Note over O,IC: Step 1: Intent Classification
    O->>IC: classify_intent(message)
    IC->>Flash: Minimal prompt
    Flash-->>IC: "handler_type"
    IC-->>O: handler_type + debug_info
    
    Note over O,H: Step 2: Handler Routing
    O->>O: _route_by_handler(handler_type)
    
    alt Static Response (welcome/small_talk/farewell)
        O-->>API: Static response
    else Sohbet Handler
        O->>LLM: Conversation prompt
        LLM-->>O: Response
    else DB Handler
        O->>DB: SQL Query
        DB-->>O: Results
        O->>LLM: Interpret results
        LLM-->>O: Analysis
    else Training Detail Handler
        O->>DB: Fetch activity data
        DB-->>O: Activity pack
        O->>LLM: Deep analysis prompt
        LLM-->>O: Detailed analysis
    end
    
    O-->>API: ChatResponse
    API-->>F: JSON response
    F-->>U: Display message
```

## Handler-Specific Flows

### 1. Static Handlers (welcome/small_talk/farewell)

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant R as Response
    
    Note over O: No LLM call needed
    O->>O: Select static response
    O->>R: GREETING_RESPONSE / SMALL_TALK_RESPONSE / FAREWELL_RESPONSE
    R-->>O: Immediate return
```

**Latency**: ~100ms (only intent classification)

### 2. Sohbet Handler

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant LLM as Gemini Pro
    
    O->>O: Build sohbet prompt
    Note over O: COACH_PERSONA + RUNNING_EXPERTISE + message
    O->>LLM: generate(prompt, max_tokens=300)
    LLM-->>O: Conversational response
    O->>O: Return ChatResponse
```

**Latency**: ~500-1000ms

### 3. DB Handler (SQL Agent)

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant SQL as SQLAgent
    participant LLM as Gemini Pro
    participant DB as PostgreSQL
    
    O->>SQL: analyze_and_answer(user_id, question)
    
    Note over SQL: Step 1: SQL Generation
    SQL->>LLM: Schema + Question → Generate SQL
    LLM-->>SQL: SQL query
    
    Note over SQL: Step 2: Validation
    SQL->>SQL: _validate_sql (SELECT only, user_id required)
    
    Note over SQL: Step 3: Execution
    SQL->>DB: Execute SQL
    DB-->>SQL: Result rows
    
    Note over SQL: Step 4: Interpretation
    SQL->>LLM: Results → Natural language
    LLM-->>SQL: Analysis text
    
    SQL-->>O: (response_text, debug_info)
```

**Latency**: ~1500-3000ms (2 LLM calls + DB query)

### 4. Training Detail Handler

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant R as Repository
    participant P as PackBuilder
    participant LLM as Gemini Pro
    participant DB as PostgreSQL
    
    O->>R: get_recent_activities(user_id)
    R->>DB: SELECT activities
    DB-->>R: Activity list
    R-->>O: Latest activity
    
    O->>P: build_pack(activity)
    P->>DB: Fetch laps, streams, biometrics
    DB-->>P: Raw data
    P-->>O: Analysis pack (tables, context)
    
    O->>LLM: COACH_PERSONA + pack + question
    LLM-->>O: Detailed analysis
```

**Latency**: ~2000-4000ms (DB queries + LLM)

## Debug Steps Output

Each handler produces debug_steps for frontend display:

```json
{
  "debug_steps": [
    {
      "step": 0,
      "name": "AI Intent Classification",
      "status": "db_handler",
      "description": "Gemini Flash → db_handler",
      "details": {
        "model": "gemini-2.0-flash-lite",
        "raw_response": "db_handler"
      }
    },
    {
      "step": 1,
      "name": "Handler",
      "status": "db_handler",
      "description": "SQL Agent sorgusu"
    },
    {
      "step": 2,
      "name": "SQL Generation",
      "status": "success"
    },
    {
      "step": 3,
      "name": "SQL Validation",
      "status": "success"
    },
    {
      "step": 4,
      "name": "SQL Execution",
      "status": "success"
    },
    {
      "step": 5,
      "name": "Result Interpretation",
      "status": "success"
    }
  ]
}
```

## Error Handling

```mermaid
flowchart TD
    A[Request Received] --> B{Intent Classification}
    B -->|Success| C{Handler Execution}
    B -->|Fail| D[Fallback Regex]
    D --> C
    C -->|Success| E[Return Response]
    C -->|LLM Error| F[Return NO_DATA_RESPONSE]
    C -->|DB Error| G[Return Error Message]
```
