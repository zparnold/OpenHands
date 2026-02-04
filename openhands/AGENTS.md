# Backend Development Guide (openhands/)

This guide provides detailed information for developing the OpenHands Python backend.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Modules](#key-modules)
3. [Development Workflow](#development-workflow)
4. [Testing Guidelines](#testing-guidelines)
5. [Code Patterns](#code-patterns)
6. [Common Tasks](#common-tasks)

---

## Architecture Overview

The OpenHands backend is a Python FastAPI application that orchestrates AI agents to perform software development tasks.

**Core architecture layers:**
```
┌─────────────────────────────────────┐
│   FastAPI Server (server/)          │ ← HTTP/WebSocket API
├─────────────────────────────────────┤
│   Controller (controller/)           │ ← Agent orchestration
├─────────────────────────────────────┤
│   Agents (agenthub/)                │ ← Task execution logic
├─────────────────────────────────────┤
│   LLM Layer (llm/)                  │ ← Language model integration
├─────────────────────────────────────┤
│   Runtime (runtime/)                │ ← Sandboxed execution
├─────────────────────────────────────┤
│   Storage (storage/)                │ ← Persistence layer
└─────────────────────────────────────┘
```

**Key concepts:**
- **Events**: Actions (agent → tool) and Observations (tool → agent)
- **State**: Agent context, history, and metrics
- **Controller**: Manages agent lifecycle and event loop
- **Runtime**: Sandboxed environment for code execution
- **Memory**: Manages conversation history within token limits

---

## Key Modules

### agenthub/
Agent implementations. Each agent has a `step()` method that takes a `State` and returns an `Action`.

**Main files:**
- `codeact_agent/`: Primary coding agent
- `browsing_agent/`: Web browsing specialist
- `dummy_agent/`: Testing/example agent

See [agenthub/AGENTS.md](agenthub/AGENTS.md) for agent development.

### controller/
Orchestrates agent execution.

**Main files:**
- `agent_controller.py`: Main control loop
- `state/state.py`: Agent state management
- `action_parser.py`: Parse LLM responses into actions
- `agent.py`: Base agent interface

### llm/
LLM integration via LiteLLM.

**Main files:**
- `llm.py`: Main LLM class with model features
- `llm_registry.py`: Model registry and configuration
- `async_llm.py`: Async LLM client
- `metrics.py`: Usage tracking
- `model_features.py`: Model capability detection

See [llm/AGENTS.md](llm/AGENTS.md) for LLM integration.

### runtime/
Sandboxed execution environments.

**Main files:**
- `base.py`: Runtime interface
- `impl/`: Runtime implementations (Docker, E2B, Modal, etc.)
- `action_execution_server.py`: REST API for executing actions
- `builder/`: Docker image builder
- `plugins/`: Runtime extensions (Jupyter, MCP, etc.)

See [runtime/AGENTS.md](runtime/AGENTS.md) for runtime implementation.

### events/
Event definitions.

**Directories:**
- `action/`: Action types (commands, files, browsing, etc.)
- `observation/`: Observation types (results, errors, etc.)
- `serialization/`: Event serialization

**Common event types:**
- `CmdRunAction` / `CmdOutputObservation`: Run bash commands
- `FileReadAction` / `FileReadObservation`: Read files
- `FileWriteAction` / `FileWriteObservation`: Write files
- `AgentFinishAction`: Mark task complete

### server/
FastAPI backend server.

**Main files:**
- `app_server/`: Main application server
- `session/`: Session management
- `routes/`: API endpoints
- `middleware/`: Request/response middleware
- `user_auth/`: User authentication (default, Entra ID)
- `routes/entra_oauth.py`: Microsoft Entra OAuth2/OIDC (authorize URL, token exchange)

**Microsoft Entra ID (Enterprise SSO):** Set `OPENHANDS_USER_AUTH_CLASS=openhands.server.user_auth.entra_user_auth.EntraUserAuth` and configure `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`. See [docs/DESIRED_FEATURES_POINT1_IMPLEMENTATION_PLAN.md](../../docs/DESIRED_FEATURES_POINT1_IMPLEMENTATION_PLAN.md).

### storage/
Data persistence.

**Main files:**
- `data_models/`: SQLAlchemy models
- `conversation/`: Conversation storage
- `files/`: File storage
- `memory/`: Agent memory management

### memory/
Manages conversation history within token limits.

**Main files:**
- `condenser.py`: Base condenser interface
- `truncation.py`: Simple truncation strategy
- Other condensers: Various strategies for summarizing history

### microagent/
Microagent system - specialized prompts for domain knowledge.

**Main files:**
- `microagent.py`: Microagent base class
- `repo_context.py`: Repository context extraction

---

## Development Workflow

### Setup

1. **Install dependencies:**
```bash
poetry install --with dev,test
```

2. **Activate virtual environment:**
```bash
poetry shell
```

3. **Install pre-commit hooks:**
```bash
poetry run pre-commit install --config ./dev_config/python/.pre-commit-config.yaml
```

### Making Changes

1. **Create/modify code** in the appropriate module
2. **Add/update tests** in `tests/unit/`
3. **Run linting:**
```bash
pre-commit run --config ./dev_config/python/.pre-commit-config.yaml
```
4. **Run tests:**
```bash
poetry run pytest tests/unit/test_xxx.py
```

### Common Issues

**Mypy errors:**
- Add type hints to function signatures
- Use `typing` module for complex types
- Add `# type: ignore` comments sparingly for known issues

**Ruff formatting:**
- Most issues are auto-fixed by `ruff format`
- Check line length (default 88 characters)
- Follow PEP 8 style guidelines

**Import order:**
- Standard library imports first
- Third-party imports second
- Local imports last
- Use `ruff` to auto-fix import order

---

## Testing Guidelines

### Test Structure

Tests are located in `tests/unit/` and mirror the `openhands/` structure:

```
tests/unit/
├── agenthub/          # Agent tests
├── controller/        # Controller tests
├── llm/              # LLM tests
├── runtime/          # Runtime tests
├── events/           # Event tests
└── ...
```

### Writing Tests

**Use pytest fixtures:**
```python
import pytest
from openhands.controller.state.state import State

@pytest.fixture
def mock_state():
    return State(
        inputs={},
        iteration=0,
    )

def test_something(mock_state):
    # Test using the fixture
    assert mock_state.iteration == 0
```

**Mock external dependencies:**
```python
from unittest.mock import AsyncMock, MagicMock, patch

@patch('openhands.llm.llm.LLM.completion')
def test_agent_step(mock_completion):
    mock_completion.return_value = AsyncMock(...)
    # Test agent
```

**Test both success and failure:**
```python
def test_file_read_success():
    # Test successful file read
    pass

def test_file_read_not_found():
    # Test file not found error
    pass
```

### Running Tests

```bash
# Run all tests
poetry run pytest tests/unit/

# Run specific module
poetry run pytest tests/unit/llm/

# Run specific test file
poetry run pytest tests/unit/test_agent.py

# Run specific test function
poetry run pytest tests/unit/test_agent.py::test_step

# Run with coverage
poetry run pytest tests/unit/ --cov=openhands --cov-report=term-missing

# Run in parallel
poetry run pytest tests/unit/ -n auto
```

---

## Code Patterns

### Async/Await

Most I/O operations are async:

```python
async def my_async_function():
    result = await some_async_call()
    return result
```

### Type Hints

Always use type hints:

```python
from typing import Optional, List, Dict, Any

def process_data(
    items: List[str],
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Process data and return result."""
    ...
```

### Error Handling

Use specific exceptions:

```python
from openhands.events.observation.error import ErrorObservation

try:
    result = risky_operation()
except FileNotFoundError as e:
    return ErrorObservation(
        content=f"File not found: {e}",
        observation_type="error",
    )
```

### Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing request", extra={
    "user_id": user_id,
    "request_id": request_id,
})
```

### Configuration

Use environment variables and config files:

```python
import os
from openhands.core.config import AppConfig

config = AppConfig()
api_key = os.getenv("API_KEY")
```

---

## Common Tasks

### Adding a New Action Type

1. Create action class in `openhands/events/action/`:
```python
from dataclasses import dataclass
from openhands.events.action.action import Action

@dataclass
class MyNewAction(Action):
    my_field: str

    @property
    def message(self) -> str:
        return f"Executing my action: {self.my_field}"
```

2. Register action in `openhands/events/action/__init__.py`

3. Handle action in runtime or agent

4. Add tests in `tests/unit/events/`

### Adding a New Observation Type

Similar to actions, create in `openhands/events/observation/`:

```python
from dataclasses import dataclass
from openhands.events.observation.observation import Observation

@dataclass
class MyNewObservation(Observation):
    result: str
    observation: str = "my_new"
```

### Adding a New LLM Model

See the "Adding New LLM Models" section in the root AGENTS.md file for detailed instructions.

### Modifying Agent Behavior

1. Edit agent implementation in `openhands/agenthub/[agent_name]/`
2. Modify prompts in `[agent_name]/prompts/`
3. Update `agent.py` for logic changes
4. Add tests in `tests/unit/agenthub/`
5. Run evaluation benchmarks (see #evaluation in Slack)

### Adding a Database Model

1. Create model in `openhands/storage/data_models/`:
```python
from sqlalchemy import Column, Integer, String
from openhands.storage.data_models.base import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id = Column(Integer, primary_key=True)
    name = Column(String)
```

2. Create migration if needed (for enterprise features)

3. Add repository/service layer

4. Add tests with SQLite in-memory database

---

## Integration Points

### With Frontend
- API endpoints in `openhands/server/routes/`
- WebSocket for real-time updates
- Event serialization via `to_dict()` methods

### With Runtime
- Actions sent to runtime via Action Execution Server
- Observations returned from runtime
- Plugin system for extending runtime capabilities

### With LLM
- `self.llm.completion()` for single completions
- `self.llm.completion_with_retries()` for retry logic
- Streaming via `stream=True` parameter

### With Storage
- Session management via `ConversationManager`
- File storage via `FileStore`
- Memory management via condensers

---

## Best Practices

1. **Type everything**: Use type hints for all function signatures
2. **Test everything**: Aim for 90%+ test coverage
3. **Document everything**: Docstrings for all public APIs
4. **Async by default**: Use async/await for I/O operations
5. **Fail fast**: Validate inputs early
6. **Log strategically**: Info for important events, debug for details
7. **Handle errors gracefully**: Return ErrorObservation, don't raise
8. **Mock external services**: Keep tests fast and reliable
9. **Use fixtures**: Share test setup via pytest fixtures
10. **Follow patterns**: Look at existing code for examples

---

## Troubleshooting

### Tests failing
- Ensure dependencies are up to date: `poetry install`
- Check for import errors
- Verify mocks are correct
- Run with `-v` for verbose output

### Linting errors
- Run `pre-commit run --all-files` to see all errors
- Use `# type: ignore` sparingly
- Fix import order with ruff
- Check line length and formatting

### Import errors
- Verify `PYTHONPATH` includes project root
- Use relative imports within openhands
- Check for circular imports

### Async issues
- All I/O should be async
- Use `await` for async functions
- Use `AsyncMock` in tests for async mocks

---

For agent-specific guidance, see [agenthub/AGENTS.md](agenthub/AGENTS.md).
For LLM integration, see [llm/AGENTS.md](llm/AGENTS.md).
For runtime development, see [runtime/AGENTS.md](runtime/AGENTS.md).
