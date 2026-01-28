# Testing Guide (tests/)

This guide provides detailed information for testing OpenHands.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Test Patterns](#test-patterns)
6. [Best Practices](#best-practices)

---

## Overview

OpenHands uses **pytest** for backend testing and **vitest** for frontend testing.

**Test types:**
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Runtime tests**: Test runtime implementations
- **End-to-end tests**: Test full user workflows

**Key principles:**
- **Fast**: Tests should run quickly
- **Isolated**: Tests should not depend on each other
- **Deterministic**: Tests should produce consistent results
- **Comprehensive**: Cover happy paths and edge cases

---

## Test Structure

### Backend Tests

```
tests/
├── unit/                   # Unit tests
│   ├── agenthub/          # Agent tests
│   ├── controller/        # Controller tests
│   ├── llm/              # LLM tests
│   ├── runtime/          # Runtime unit tests
│   ├── events/           # Event tests
│   ├── server/           # Server tests
│   ├── storage/          # Storage tests
│   └── ...
├── runtime/               # Runtime integration tests
│   ├── utils/            # Runtime utilities tests
│   └── trajs/            # Test trajectories
└── e2e/                   # End-to-end tests
```

### Frontend Tests

```
frontend/
├── __tests__/             # Component tests
├── tests/                 # Integration tests
└── src/
    └── */
        └── *.test.tsx     # Co-located component tests
```

---

## Running Tests

### Backend Tests

**Run all unit tests:**
```bash
poetry run pytest tests/unit/
```

**Run specific module:**
```bash
poetry run pytest tests/unit/llm/
```

**Run specific test file:**
```bash
poetry run pytest tests/unit/test_agent.py
```

**Run specific test function:**
```bash
poetry run pytest tests/unit/test_agent.py::test_step
```

**Run with coverage:**
```bash
poetry run pytest tests/unit/ --cov=openhands --cov-report=term-missing
```

**Run in parallel:**
```bash
poetry run pytest tests/unit/ -n auto
```

**Run with verbose output:**
```bash
poetry run pytest tests/unit/ -v
```

**Run matching pattern:**
```bash
poetry run pytest tests/unit/ -k "test_agent"
```

### Frontend Tests

**Run all tests:**
```bash
cd frontend
npm run test
```

**Run specific tests:**
```bash
npm run test -- -t "TestName"
```

**Run in watch mode:**
```bash
npm run test -- --watch
```

**Run with coverage:**
```bash
npm run test -- --coverage
```

### Enterprise Tests

**Full test suite:**
```bash
cd enterprise
PYTHONPATH=".:$PYTHONPATH" poetry run pytest --forked -n auto -s tests/unit/ --cov=enterprise --cov-branch
```

**Specific module:**
```bash
cd enterprise
PYTHONPATH=".:$PYTHONPATH" poetry run pytest tests/unit/telemetry/ --confcutdir=tests/unit/telemetry
```

---

## Writing Tests

### Basic Unit Test

```python
# tests/unit/test_example.py
import pytest
from openhands.example import my_function

def test_my_function():
    """Test my_function with valid input."""
    result = my_function(input_value=5)
    assert result == 10

def test_my_function_edge_case():
    """Test my_function with edge case."""
    result = my_function(input_value=0)
    assert result == 0

def test_my_function_error():
    """Test my_function raises error."""
    with pytest.raises(ValueError):
        my_function(input_value=-1)
```

### Using Fixtures

```python
import pytest

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

@pytest.fixture
def mock_llm():
    """Provide mock LLM for tests."""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="test"))]
    )
    return llm

def test_with_fixture(sample_data, mock_llm):
    """Test using fixtures."""
    assert sample_data["key"] == "value"
    assert mock_llm.completion() is not None
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    from openhands.example import async_function
    
    result = await async_function()
    assert result is not None
```

### Mocking

```python
from unittest.mock import MagicMock, AsyncMock, patch

def test_with_mock():
    """Test with mock object."""
    mock = MagicMock()
    mock.method.return_value = "mocked"
    
    result = mock.method()
    assert result == "mocked"
    mock.method.assert_called_once()

@pytest.mark.asyncio
async def test_with_async_mock():
    """Test with async mock."""
    mock = AsyncMock()
    mock.async_method.return_value = "async mocked"
    
    result = await mock.async_method()
    assert result == "async mocked"

@patch('openhands.example.external_function')
def test_with_patch(mock_external):
    """Test with patched function."""
    mock_external.return_value = "patched"
    
    from openhands.example import my_function
    result = my_function()
    
    assert result == "patched"
    mock_external.assert_called_once()
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_parametrized(input_value, expected):
    """Test with multiple inputs."""
    result = input_value * 2
    assert result == expected
```

### Testing Agents

```python
import pytest
from unittest.mock import MagicMock
from openhands.agenthub.codeact_agent.agent import CodeActAgent
from openhands.controller.state.state import State
from openhands.events.action import Action

def test_agent_initialization():
    """Test agent initialization."""
    llm = MagicMock()
    agent = CodeActAgent(llm)
    
    assert agent.llm == llm
    assert agent.VERSION is not None

def test_agent_step():
    """Test agent step function."""
    llm = MagicMock()
    llm.completion.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="<execute>echo test</execute>"
                )
            )
        ]
    )
    
    agent = CodeActAgent(llm)
    state = State(inputs={}, iteration=0)
    
    action = agent.step(state)
    
    assert isinstance(action, Action)
    assert llm.completion.called
```

### Testing with Database

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from openhands.storage.data_models.base import Base

@pytest.fixture
async def db_session():
    """Create in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_database_operation(db_session):
    """Test database operation."""
    from openhands.storage.data_models.user import User
    
    # Create user
    user = User(username="test", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    # Query user
    result = await db_session.execute(
        select(User).where(User.username == "test")
    )
    fetched_user = result.scalar_one()
    
    assert fetched_user.username == "test"
```

### Frontend Component Tests

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MyComponent } from './my-component';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('handles user interactions', async () => {
    const { user } = render(<MyComponent />);
    
    const button = screen.getByRole('button');
    await user.click(button);
    
    expect(screen.getByText('Clicked')).toBeInTheDocument();
  });
});
```

---

## Test Patterns

### Arrange-Act-Assert Pattern

```python
def test_example():
    """Follow AAA pattern."""
    # Arrange - Set up test data
    input_value = 5
    expected = 10
    
    # Act - Execute the code under test
    result = my_function(input_value)
    
    # Assert - Verify the result
    assert result == expected
```

### Given-When-Then Pattern

```python
def test_example():
    """Follow GWT pattern."""
    # Given - Initial state
    user = create_user(username="test")
    
    # When - Action occurs
    updated_user = update_user(user, email="new@example.com")
    
    # Then - Expected outcome
    assert updated_user.email == "new@example.com"
```

### Test Doubles

**Dummy:**
```python
def test_with_dummy():
    """Use dummy object (not actually used)."""
    dummy = object()
    result = process_data(dummy)  # dummy not actually used
    assert result is not None
```

**Stub:**
```python
def test_with_stub():
    """Use stub (returns predetermined values)."""
    class StubLLM:
        def completion(self, **kwargs):
            return "stubbed response"
    
    agent = MyAgent(StubLLM())
    # Test agent behavior with stubbed LLM
```

**Mock:**
```python
def test_with_mock():
    """Use mock (verify interactions)."""
    from unittest.mock import MagicMock
    
    mock_llm = MagicMock()
    agent = MyAgent(mock_llm)
    agent.step(state)
    
    # Verify mock was called correctly
    mock_llm.completion.assert_called_once()
```

**Fake:**
```python
def test_with_fake():
    """Use fake (working implementation)."""
    class FakeDatabase:
        def __init__(self):
            self.data = {}
        
        def get(self, key):
            return self.data.get(key)
        
        def set(self, key, value):
            self.data[key] = value
    
    db = FakeDatabase()
    service = MyService(db)
    # Test service with fake database
```

---

## Best Practices

### 1. Test One Thing at a Time

```python
# Bad - tests multiple things
def test_user_operations():
    user = create_user()
    user.update_email()
    user.delete()
    assert True

# Good - separate tests
def test_create_user():
    user = create_user()
    assert user is not None

def test_update_user_email():
    user = create_user()
    user.update_email("new@example.com")
    assert user.email == "new@example.com"

def test_delete_user():
    user = create_user()
    user.delete()
    assert user.deleted is True
```

### 2. Use Descriptive Test Names

```python
# Bad
def test_1():
    pass

# Good
def test_agent_returns_finish_action_when_task_complete():
    pass
```

### 3. Test Edge Cases

```python
def test_divide():
    """Test normal division."""
    assert divide(10, 2) == 5

def test_divide_by_zero():
    """Test division by zero."""
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_negative_numbers():
    """Test division with negative numbers."""
    assert divide(-10, 2) == -5
    assert divide(10, -2) == -5
```

### 4. Mock External Dependencies

```python
@patch('openhands.example.external_api_call')
def test_function(mock_api):
    """Mock external API calls."""
    mock_api.return_value = {"status": "success"}
    
    result = my_function_that_calls_api()
    
    assert result is not None
    mock_api.assert_called_once()
```

### 5. Use Fixtures for Common Setup

```python
@pytest.fixture
def agent():
    """Common agent fixture."""
    llm = MagicMock()
    return MyAgent(llm)

@pytest.fixture
def state():
    """Common state fixture."""
    return State(inputs={}, iteration=0)

def test_agent_step(agent, state):
    """Use fixtures."""
    action = agent.step(state)
    assert action is not None
```

### 6. Test Async Code Properly

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None

@pytest.mark.asyncio
async def test_async_with_mock():
    """Test async function with mock."""
    from unittest.mock import AsyncMock
    
    mock = AsyncMock()
    mock.async_method.return_value = "result"
    
    result = await mock.async_method()
    assert result == "result"
```

### 7. Use Test Coverage

```bash
# Generate coverage report
poetry run pytest tests/unit/ --cov=openhands --cov-report=html

# View report
open htmlcov/index.html
```

### 8. Keep Tests Independent

```python
# Bad - tests depend on each other
def test_create_user():
    global user
    user = create_user()

def test_update_user():
    user.update()  # Depends on test_create_user

# Good - independent tests
def test_create_user():
    user = create_user()
    assert user is not None

def test_update_user():
    user = create_user()  # Create own user
    user.update()
    assert user.updated is True
```

### 9. Test Error Conditions

```python
def test_success_case():
    """Test successful execution."""
    result = my_function(valid_input)
    assert result is not None

def test_invalid_input():
    """Test with invalid input."""
    with pytest.raises(ValueError):
        my_function(invalid_input)

def test_network_error():
    """Test network error handling."""
    with patch('requests.get', side_effect=requests.RequestException):
        result = my_function_that_uses_network()
        assert result is None  # Or appropriate error handling
```

### 10. Document Test Purpose

```python
def test_agent_delegates_to_browsing_agent_for_web_tasks():
    """
    Test that CodeActAgent correctly delegates web browsing tasks
    to BrowsingAgent when it determines the task requires web access.
    
    This is important because:
    1. BrowsingAgent is specialized for web tasks
    2. Delegation improves task completion quality
    3. It demonstrates multi-agent coordination
    """
    # Test implementation
    pass
```

---

## Common Testing Scenarios

### Testing Agents

```python
def test_agent_completes_simple_task():
    """Test agent can complete simple task."""
    llm = MagicMock()
    llm.completion.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="<execute>echo done</execute>"
                )
            )
        ]
    )
    
    agent = CodeActAgent(llm)
    state = State(
        inputs={"task": "print done"},
        iteration=0
    )
    
    action = agent.step(state)
    assert isinstance(action, CmdRunAction)
    assert "echo done" in action.command
```

### Testing LLM Integration

```python
@patch('openhands.llm.llm.litellm.completion')
def test_llm_completion(mock_completion):
    """Test LLM completion."""
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="test"))]
    )
    
    llm = LLM(model="gpt-4")
    response = llm.completion(
        messages=[{"role": "user", "content": "test"}]
    )
    
    assert response.choices[0].message.content == "test"
```

### Testing Runtime

```python
@pytest.mark.asyncio
async def test_runtime_execute_command():
    """Test runtime command execution."""
    config = AppConfig(runtime="local")
    runtime = create_runtime(config)
    
    await runtime.connect()
    
    action = CmdRunAction(command="echo test")
    observation = await runtime.run_action(action)
    
    assert "test" in observation.content
    
    await runtime.close()
```

### Testing API Endpoints

```python
from fastapi.testclient import TestClient
from openhands.server.app import app

client = TestClient(app)

def test_api_endpoint():
    """Test API endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_post():
    """Test POST endpoint."""
    response = client.post(
        "/api/messages",
        json={"content": "test"}
    )
    assert response.status_code == 201
```

---

## Troubleshooting

### Tests Failing Intermittently
- Check for race conditions
- Use proper async/await
- Mock time-dependent code
- Set random seeds for determinism

### Slow Tests
- Use mocks instead of real services
- Run tests in parallel (`-n auto`)
- Use fixtures for expensive setup
- Profile tests to find bottlenecks

### Import Errors
- Verify `PYTHONPATH` is set correctly
- Check for circular imports
- Use relative imports
- Run from project root

### Mock Not Working
- Verify correct import path
- Use `patch` at the right level
- Check if function is already imported
- Use `return_value` or `side_effect`

### Async Test Failures
- Use `@pytest.mark.asyncio` decorator
- Use `AsyncMock` for async functions
- Await all async operations
- Check for unhandled exceptions

---

For backend testing patterns, see [../openhands/AGENTS.md](../openhands/AGENTS.md).
For frontend testing patterns, see [../frontend/AGENTS.md](../frontend/AGENTS.md).
For enterprise testing, see [../enterprise/AGENTS.md](../enterprise/AGENTS.md).
