# LLM Integration Guide (openhands/llm/)

This guide provides detailed information for working with LLMs in OpenHands.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Using LLMs](#using-llms)
4. [Adding New Models](#adding-new-models)
5. [Model Features](#model-features)
6. [Best Practices](#best-practices)

---

## Overview

The OpenHands LLM module wraps **LiteLLM** to provide a unified interface for multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude)
- Google (Gemini, PaLM)
- Mistral
- OpenHands managed provider
- Many others via LiteLLM

**Key features:**
- Unified API across providers
- Streaming support
- Function calling
- Prompt caching
- Rate limiting and retries
- Usage metrics
- Async/await support

---

## Architecture

```
┌─────────────────────────────────────┐
│   Agent (uses self.llm)             │
├─────────────────────────────────────┤
│   LLM Class (llm.py)                │ ← OpenHands wrapper
├─────────────────────────────────────┤
│   LiteLLM (third-party)             │ ← Unified LLM interface
├─────────────────────────────────────┤
│   Provider APIs (OpenAI, etc.)      │ ← Actual LLM services
└─────────────────────────────────────┘
```

**Key files:**
- `llm.py`: Main LLM class with completion methods
- `async_llm.py`: Async LLM client
- `llm_registry.py`: Model registry and configuration
- `llm_utils.py`: Utility functions
- `model_features.py`: Model capability detection
- `metrics.py`: Usage tracking
- `fn_call_converter.py`: Function calling conversion
- `retry_mixin.py`: Retry logic
- `debug_mixin.py`: Debug utilities

---

## Using LLMs

### Basic Usage (Sync)

```python
from openhands.llm import LLM

# Create LLM instance
llm = LLM(
    model="gpt-4",
    api_key="your-api-key",
    temperature=0.0,
)

# Make completion call
response = llm.completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
)

# Extract response
content = response.choices[0].message.content
print(content)
```

### Async Usage

```python
from openhands.llm import AsyncLLM

# Create async LLM instance
llm = AsyncLLM(
    model="gpt-4",
    api_key="your-api-key",
)

# Make async completion call
async def get_completion():
    response = await llm.completion(
        messages=[
            {"role": "user", "content": "Hello!"},
        ],
    )
    return response.choices[0].message.content
```

### Streaming

```python
# Stream response
response = llm.completion(
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### With Retries

```python
# Automatically retry on rate limits or transient errors
response = llm.completion_with_retries(
    messages=[{"role": "user", "content": "Hello"}],
    max_retries=3,
)
```

### Function Calling

```python
# Define functions
functions = [
    {
        "name": "get_weather",
        "description": "Get the weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name",
                },
            },
            "required": ["location"],
        },
    }
]

# Call LLM with functions
response = llm.completion(
    messages=[{"role": "user", "content": "What's the weather in London?"}],
    functions=functions,
)

# Check if function was called
if response.choices[0].message.function_call:
    function_name = response.choices[0].message.function_call.name
    arguments = json.loads(response.choices[0].message.function_call.arguments)
    print(f"Function: {function_name}, Args: {arguments}")
```

### In Agent Context

```python
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.events.action import Action, MessageAction

class MyAgent(Agent):
    def step(self, state: State) -> Action:
        """Use self.llm to interact with language model."""
        messages = self.build_messages(state)
        
        # Call LLM
        response = self.llm.completion(
            messages=messages,
            temperature=0.0,
            stop=["</execute>"],  # Optional stop sequences
        )
        
        # Parse response
        content = response.choices[0].message.content
        return MessageAction(content=content)
```

---

## Adding New Models

To add a new LLM model to OpenHands:

### 1. Frontend Model Arrays

Edit `frontend/src/utils/verified-models.ts`:

```typescript
export const VERIFIED_MODELS = [
  // ... existing models
  'new-model-name',
];

// Add to provider-specific array
export const VERIFIED_OPENAI_MODELS = [
  // ... existing models
  'new-model-name',
];
```

### 2. Backend CLI Integration

Edit `openhands/cli/utils.py`:

```python
VERIFIED_OPENAI_MODELS = [
    # ... existing models
    'new-model-name',
]
```

### 3. Backend Model List

Edit `openhands/utils/llm.py`:

```python
# CRITICAL: Add to openhands_models if using OpenHands provider
openhands_models = [
    # ... existing models
    'openhands/new-model-name',
]
```

### 4. Backend LLM Configuration

Edit `openhands/llm/llm.py`:

```python
# Add to feature-specific arrays based on capabilities

# If model supports function calling
FUNCTION_CALLING_SUPPORTED_MODELS = [
    # ... existing models
    'new-model-name',
]

# If model supports reasoning effort (like o1, o3)
REASONING_EFFORT_SUPPORTED_MODELS = [
    # ... existing models
    'new-model-name',
]

# If model supports prompt caching
CACHE_PROMPT_SUPPORTED_MODELS = [
    # ... existing models
    'new-model-name',
]

# If model doesn't support stop words
MODELS_WITHOUT_STOP_WORDS = [
    # ... existing models
    'new-model-name',
]
```

### 5. Validation

```bash
# Backend linting
pre-commit run --config ./dev_config/python/.pre-commit-config.yaml

# Frontend linting
cd frontend && npm run lint:fix

# Frontend build
cd frontend && npm run build
```

---

## Model Features

### Model Feature Detection

OpenHands automatically detects model capabilities:

```python
from openhands.llm.model_features import ModelFeatures

features = ModelFeatures(model="gpt-4")

# Check capabilities
if features.supports_function_calling:
    # Use function calling
    pass

if features.supports_prompt_caching:
    # Enable prompt caching
    pass

if features.supports_reasoning_effort:
    # Set reasoning effort parameter
    pass
```

### Feature Arrays

**FUNCTION_CALLING_SUPPORTED_MODELS:**
Models that support structured function calling (tool use).

Examples: GPT-4, GPT-3.5-turbo, Claude 3+

**REASONING_EFFORT_SUPPORTED_MODELS:**
Models that support reasoning effort parameters (thinking time).

Examples: o1, o3

**CACHE_PROMPT_SUPPORTED_MODELS:**
Models that support prompt caching for efficiency.

Examples: Claude 3+, some GPT models

**MODELS_WITHOUT_STOP_WORDS:**
Models that don't support stop word parameters.

Examples: o1, o3

### Checking Model Support

```python
def step(self, state: State) -> Action:
    # Check if function calling is supported
    if self.llm.model in FUNCTION_CALLING_SUPPORTED_MODELS:
        response = self.llm.completion(
            messages=messages,
            functions=functions,
        )
    else:
        # Fallback to regular completion
        response = self.llm.completion(
            messages=messages,
        )
```

---

## Best Practices

### 1. Use Temperature Wisely

```python
# For deterministic outputs (code, structured data)
response = llm.completion(
    messages=messages,
    temperature=0.0,
)

# For creative outputs (text generation)
response = llm.completion(
    messages=messages,
    temperature=0.7,
)
```

### 2. Handle Errors Gracefully

```python
from openhands.llm.exceptions import LLMError

try:
    response = llm.completion(messages=messages)
except LLMError as e:
    # Handle LLM-specific errors
    print(f"LLM Error: {e}")
except Exception as e:
    # Handle general errors
    print(f"Error: {e}")
```

### 3. Use Stop Sequences

```python
# Define stop sequences to control output
response = llm.completion(
    messages=messages,
    stop=["</execute>", "```", "---"],
)
```

### 4. Monitor Token Usage

```python
response = llm.completion(messages=messages)

# Get token usage
usage = response.usage
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Completion tokens: {usage.completion_tokens}")
print(f"Total tokens: {usage.total_tokens}")
```

### 5. Use Prompt Caching

```python
# For models that support prompt caching
if self.llm.model in CACHE_PROMPT_SUPPORTED_MODELS:
    response = llm.completion(
        messages=messages,
        cache_prompt=True,  # Cache system prompt
    )
```

### 6. Stream Long Responses

```python
def stream_response(self, messages):
    """Stream long responses to avoid timeouts."""
    response = self.llm.completion(
        messages=messages,
        stream=True,
    )
    
    content = ""
    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        content += delta
        # Optionally emit partial updates
    
    return content
```

### 7. Use Reasoning Effort

```python
# For models like o1, o3 that support reasoning effort
if self.llm.model in REASONING_EFFORT_SUPPORTED_MODELS:
    response = llm.completion(
        messages=messages,
        reasoning_effort="high",  # or "medium", "low"
    )
```

### 8. Validate Function Call Arguments

```python
import json

if response.choices[0].message.function_call:
    try:
        args = json.loads(response.choices[0].message.function_call.arguments)
        # Validate args
        if "location" in args:
            # Safe to use
            location = args["location"]
    except json.JSONDecodeError:
        # Handle invalid JSON
        pass
```

### 9. Use Model-Specific Settings

```python
class MyAgent(Agent):
    def __init__(self, llm, config=None):
        super().__init__(llm, config)
        
        # Adjust settings based on model
        if "gpt-4" in llm.model:
            self.max_tokens = 8000
        elif "claude" in llm.model:
            self.max_tokens = 100000
        else:
            self.max_tokens = 4000
```

### 10. Test with Multiple Models

```python
@pytest.mark.parametrize("model", [
    "gpt-4",
    "gpt-3.5-turbo",
    "claude-3-opus",
])
def test_agent_with_model(model):
    """Test agent with different models."""
    llm = LLM(model=model)
    agent = MyAgent(llm)
    # Test agent
```

---

## Advanced Topics

### Custom LLM Provider

```python
from openhands.llm import LLM

# Use custom provider via LiteLLM
llm = LLM(
    model="custom-provider/model-name",
    api_base="https://custom-api.example.com/v1",
    api_key="your-api-key",
)
```

### Prompt Engineering

```python
def build_system_prompt(self) -> str:
    """Build effective system prompt."""
    return """You are an AI assistant that helps with coding tasks.

Your capabilities:
- Write and execute Python code
- Read and modify files
- Run bash commands
- Browse the web

Your responses should:
1. Think step-by-step
2. Be concise and clear
3. Include code when relevant
4. Verify your work

Current task: {task}
"""

def build_user_prompt(self, state: State) -> str:
    """Build context-aware user prompt."""
    # Include recent history
    recent_events = state.history[-5:]
    
    # Format events
    context = "\n".join([
        f"- {event}" for event in recent_events
    ])
    
    return f"""Recent actions:
{context}

What should we do next?"""
```

### Metrics and Monitoring

```python
from openhands.llm.metrics import LLMMetrics

# Track LLM usage
metrics = LLMMetrics()

response = llm.completion(messages=messages)

# Update metrics
metrics.record_completion(
    model=llm.model,
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    cost=response.usage.total_cost,
)

# Get metrics
print(f"Total calls: {metrics.total_calls}")
print(f"Total cost: ${metrics.total_cost}")
print(f"Total tokens: {metrics.total_tokens}")
```

### Batch Completions

```python
async def batch_completions(self, message_lists):
    """Process multiple completions in parallel."""
    import asyncio
    
    async_llm = AsyncLLM(model=self.llm.model)
    
    tasks = [
        async_llm.completion(messages=messages)
        for messages in message_lists
    ]
    
    responses = await asyncio.gather(*tasks)
    return responses
```

---

## Configuration

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="your-key"

# Anthropic
export ANTHROPIC_API_KEY="your-key"

# Google
export GOOGLE_API_KEY="your-key"

# Custom provider
export CUSTOM_API_KEY="your-key"
export CUSTOM_API_BASE="https://api.example.com/v1"
```

### LLM Config Object

```python
from openhands.core.config import LLMConfig

llm_config = LLMConfig(
    model="gpt-4",
    api_key="your-key",
    temperature=0.0,
    max_tokens=4000,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
)

llm = LLM.from_config(llm_config)
```

---

## Troubleshooting

### Rate Limiting

```python
# Use completion_with_retries for automatic retry
response = llm.completion_with_retries(
    messages=messages,
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0,
)
```

### Timeout Issues

```python
# Set timeout
response = llm.completion(
    messages=messages,
    timeout=60.0,  # seconds
)
```

### Model Not Found

```python
# Verify model name
from openhands.llm.llm_registry import get_available_models

available = get_available_models()
print(f"Available models: {available}")
```

### Function Calling Errors

```python
# Check if model supports function calling
if llm.model not in FUNCTION_CALLING_SUPPORTED_MODELS:
    print(f"Warning: {llm.model} does not support function calling")
```

### Token Limit Exceeded

```python
# Estimate token count
from openhands.llm.llm_utils import count_tokens

token_count = count_tokens(messages)
if token_count > MAX_TOKENS:
    # Truncate or condense messages
    messages = condense_messages(messages)
```

---

## Testing LLMs

### Mock LLM for Tests

```python
from unittest.mock import MagicMock

def test_agent_with_mock_llm():
    """Test agent with mocked LLM."""
    llm = MagicMock()
    llm.completion.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="Test response",
                    function_call=None,
                )
            )
        ],
        usage=MagicMock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )
    
    agent = MyAgent(llm)
    action = agent.step(state)
    
    # Verify LLM was called
    llm.completion.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.integration
def test_agent_with_real_llm():
    """Test agent with real LLM (requires API key)."""
    import os
    
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No API key available")
    
    llm = LLM(model="gpt-3.5-turbo")
    agent = MyAgent(llm)
    
    state = State(inputs={}, iteration=0)
    action = agent.step(state)
    
    assert action is not None
```

---

For agent development, see [../agenthub/AGENTS.md](../agenthub/AGENTS.md).
For backend development, see [../AGENTS.md](../AGENTS.md).
For general guidelines, see [../../AGENTS.md](../../AGENTS.md).
