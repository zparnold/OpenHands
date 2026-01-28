# Agent Development Guide (openhands/agenthub/)

This guide provides detailed information for developing agents in OpenHands.

## Table of Contents

1. [What is an Agent?](#what-is-an-agent)
2. [Agent Architecture](#agent-architecture)
3. [Creating an Agent](#creating-an-agent)
4. [Agent State](#agent-state)
5. [Actions and Observations](#actions-and-observations)
6. [Agent Delegation](#agent-delegation)
7. [Best Practices](#best-practices)

---

## What is an Agent?

An agent is the core AI entity in OpenHands that performs software development tasks by:
- Interacting with language models (LLMs)
- Executing actions (running commands, editing files, browsing web)
- Processing observations (command output, file contents, errors)
- Making decisions based on state and history

**Available agents:**
- **CodeActAgent**: Primary agent that writes and executes code
- **BrowsingAgent**: Specialized for web browsing tasks
- **DummyAgent**: Simple agent for testing
- **ReadOnlyAgent**: Agent with read-only permissions
- **VisualBrowsingAgent**: Browser agent with visual capabilities
- **LOCAgent**: Specialized agent for localization tasks

---

## Agent Architecture

Every agent in OpenHands follows this interface:

```python
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.events.action import Action

class MyAgent(Agent):
    def step(self, state: State) -> Action:
        """
        Take one step towards the goal.
        
        Args:
            state: Current agent state
            
        Returns:
            Action to execute
        """
        # 1. Analyze state
        # 2. Call LLM
        # 3. Parse response
        # 4. Return action
        pass
```

**Key components:**
- `self.llm`: LiteLLM client for language model calls
- `state`: Agent state (history, metrics, delegates)
- `Action`: Operation to perform
- `Observation`: Result of action

**Agent loop:**
```
1. Agent receives State
2. Agent calls step(state) → Action
3. Action executed in runtime
4. Runtime returns Observation
5. Observation added to State
6. Loop continues until AgentFinishAction
```

---

## Creating an Agent

### Step 1: Create Agent Directory

```bash
mkdir openhands/agenthub/my_agent
touch openhands/agenthub/my_agent/__init__.py
touch openhands/agenthub/my_agent/agent.py
```

### Step 2: Implement Agent Class

```python
# openhands/agenthub/my_agent/agent.py
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.events.action import Action, AgentFinishAction, MessageAction
from openhands.events.observation import Observation

class MyAgent(Agent):
    """My custom agent implementation."""
    
    VERSION = "1.0"
    
    def __init__(self, llm, config=None):
        """Initialize agent."""
        super().__init__(llm, config)
        # Custom initialization
    
    def step(self, state: State) -> Action:
        """Take one step towards the goal."""
        # Get latest events
        if state.history:
            latest = state.history[-1]
            
            # Check if we should finish
            if self.should_finish(state):
                return AgentFinishAction()
        
        # Call LLM
        messages = self.build_messages(state)
        response = self.llm.completion(
            messages=messages,
            temperature=0.0,
            stop=["</execute>"],  # Optional stop sequences
        )
        
        # Parse response into action
        action = self.parse_response(response)
        return action
    
    def build_messages(self, state: State) -> list:
        """Build LLM prompt from state."""
        messages = [
            {"role": "system", "content": self.system_prompt()},
        ]
        
        # Add conversation history
        for event in state.history:
            if isinstance(event, Action):
                messages.append({
                    "role": "assistant",
                    "content": str(event),
                })
            elif isinstance(event, Observation):
                messages.append({
                    "role": "user",
                    "content": event.content,
                })
        
        return messages
    
    def system_prompt(self) -> str:
        """Return system prompt for agent."""
        return """You are a helpful AI assistant..."""
    
    def parse_response(self, response) -> Action:
        """Parse LLM response into an action."""
        content = response.choices[0].message.content
        # Parse content and return appropriate action
        return MessageAction(content=content)
    
    def should_finish(self, state: State) -> bool:
        """Check if agent should finish."""
        # Custom logic to determine if task is complete
        return False
```

### Step 3: Register Agent

Add to `openhands/agenthub/__init__.py`:

```python
from .my_agent.agent import MyAgent

__all__ = [
    # ... existing agents
    'MyAgent',
]
```

### Step 4: Add Tests

```python
# tests/unit/agenthub/test_my_agent.py
import pytest
from unittest.mock import MagicMock
from openhands.agenthub.my_agent.agent import MyAgent
from openhands.controller.state.state import State
from openhands.events.action import AgentFinishAction

def test_my_agent_step():
    """Test agent step function."""
    llm = MagicMock()
    agent = MyAgent(llm)
    
    state = State(inputs={}, iteration=0)
    action = agent.step(state)
    
    assert action is not None
```

---

## Agent State

The `State` object contains:

**Multi-agent state:**
- `root_task`: Main task from user
- `subtask`: Current subtask (for delegation)
- `iteration`: Global iteration counter
- `local_iteration`: Local iteration counter
- `delegate_level`: Nesting level of delegation

**Running state:**
- `agent_state`: Current state (LOADING, RUNNING, PAUSED, etc.)
- `traffic_control_state`: Rate limiting state
- `confirmation_mode`: User confirmation required
- `last_error`: Most recent error

**History:**
- `history`: List of events (actions + observations)
- `start_id`, `end_id`: Event range for current session

**Metrics:**
- `global_metrics`: Overall task metrics
- `local_metrics`: Subtask metrics

**Extra data:**
- `extra_data`: Task-specific data

**Usage:**
```python
def step(self, state: State) -> Action:
    # Access history
    for event in state.history:
        if isinstance(event, CmdOutputObservation):
            print(event.content)
    
    # Check iterations
    if state.iteration > state.max_iterations:
        return AgentFinishAction()
    
    # Access metrics
    cost = state.global_metrics.accumulated_cost
```

---

## Actions and Observations

### Available Actions

**Command execution:**
```python
from openhands.events.action import CmdRunAction, IPythonRunCellAction

# Run bash command
action = CmdRunAction(command="ls -la")

# Run Python code
action = IPythonRunCellAction(code="print('hello')")
```

**File operations:**
```python
from openhands.events.action import FileReadAction, FileWriteAction

# Read file
action = FileReadAction(path="/path/to/file.py")

# Write file
action = FileWriteAction(path="/path/to/file.py", content="...")
```

**Web browsing:**
```python
from openhands.events.action import BrowseURLAction

action = BrowseURLAction(url="https://example.com")
```

**Task management:**
```python
from openhands.events.action import AddTaskAction, ModifyTaskAction

# Add subtask
action = AddTaskAction(
    parent="main_task",
    goal="subtask goal",
    subtasks=[]
)

# Modify task
action = ModifyTaskAction(task_id="123", state="completed")
```

**Agent control:**
```python
from openhands.events.action import AgentFinishAction, AgentRejectAction

# Complete task successfully
action = AgentFinishAction(outputs={"result": "success"})

# Reject task
action = AgentRejectAction(outputs={"reason": "cannot complete"})
```

**Messaging:**
```python
from openhands.events.action import MessageAction

action = MessageAction(content="Thinking about the problem...")
```

### Serialization

```python
# Serialize for UI (user-friendly)
action_dict = action.to_dict()

# Serialize for LLM (includes raw details)
action_memory = action.to_memory()

# Deserialize
from openhands.events.serialization import action_from_dict
action = action_from_dict(action_dict)
```

### Available Observations

```python
from openhands.events.observation import (
    CmdOutputObservation,      # Command output
    FileReadObservation,        # File contents
    FileWriteObservation,       # Write confirmation
    BrowserOutputObservation,   # Browser content
    ErrorObservation,           # Error message
    SuccessObservation,         # Success message
)
```

---

## Agent Delegation

OpenHands supports multi-agent systems where agents can delegate tasks.

### Terminology

- **Task**: End-to-end conversation between system and user
- **Subtask**: Conversation between agent and user/agent
- **Delegate**: Agent that executes a subtask
- **Delegate level**: Nesting depth of delegation

### Delegation Example

```
-- TASK STARTS (SUBTASK 0 STARTS) --

DELEGATE_LEVEL 0, ITERATION 0, LOCAL_ITERATION 0
CodeActAgent: I should request help from BrowsingAgent

-- DELEGATE STARTS (SUBTASK 1 STARTS) --

DELEGATE_LEVEL 1, ITERATION 1, LOCAL_ITERATION 0
BrowsingAgent: Let me find the answer on GitHub

DELEGATE_LEVEL 1, ITERATION 2, LOCAL_ITERATION 1
BrowsingAgent: I found the answer, let me finish

-- DELEGATE ENDS (SUBTASK 1 ENDS) --

DELEGATE_LEVEL 0, ITERATION 3, LOCAL_ITERATION 1
CodeActAgent: I got the answer, let me finish

-- TASK ENDS (SUBTASK 0 ENDS) --
```

**Note:** 
- `ITERATION` is global across all agents
- `LOCAL_ITERATION` is local to each subtask

### Implementing Delegation

```python
from openhands.events.action import AddTaskAction

def step(self, state: State) -> Action:
    # Decide to delegate
    if self.should_delegate(state):
        return AddTaskAction(
            parent=state.root_task,
            goal="Browse GitHub to find stars count",
            subtasks=[],
            agent="BrowsingAgent",  # Specify agent to delegate to
        )
    
    # Continue with own task
    return self.execute_task(state)
```

---

## Best Practices

### 1. Use Prompts Directory

Create a `prompts/` directory for prompt templates:

```
my_agent/
├── __init__.py
├── agent.py
└── prompts/
    ├── system.j2
    └── user.j2
```

Use Jinja2 templates:
```python
from jinja2 import Environment, FileSystemLoader

def load_prompt(name: str, **kwargs) -> str:
    env = Environment(loader=FileSystemLoader('prompts'))
    template = env.get_template(f'{name}.j2')
    return template.render(**kwargs)
```

### 2. Handle Errors Gracefully

```python
def step(self, state: State) -> Action:
    try:
        # Agent logic
        return action
    except Exception as e:
        return MessageAction(
            content=f"Error: {str(e)}"
        )
```

### 3. Use Memory Condensers

For long conversations, use memory condensers:

```python
from openhands.memory import get_condenser

condenser = get_condenser("truncation")
condensed_history = condenser.condense(
    state.history,
    max_tokens=4000
)
```

### 4. Test with Mock LLM

```python
def test_agent():
    from unittest.mock import MagicMock
    
    llm = MagicMock()
    llm.completion.return_value = MagicMock(
        choices=[
            MagicMock(message=MagicMock(content="test response"))
        ]
    )
    
    agent = MyAgent(llm)
    state = State(inputs={}, iteration=0)
    action = agent.step(state)
    
    assert action is not None
```

### 5. Implement Reasoning

Add thought process to actions:

```python
action = CmdRunAction(
    command="ls -la",
    thought="Listing directory to understand structure"
)
```

### 6. Use Function Calling

For structured outputs, use function calling:

```python
response = self.llm.completion(
    messages=messages,
    functions=[{
        "name": "execute_command",
        "description": "Execute a bash command",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
        },
    }],
)

# Parse function call
if response.choices[0].message.function_call:
    args = json.loads(response.choices[0].message.function_call.arguments)
    return CmdRunAction(command=args["command"])
```

### 7. Add Versioning

```python
class MyAgent(Agent):
    VERSION = "1.0"  # Track agent versions
```

### 8. Document Agent Behavior

```python
class MyAgent(Agent):
    """
    My custom agent that performs specific tasks.
    
    Capabilities:
    - Task 1
    - Task 2
    
    Limitations:
    - Cannot do X
    - Requires Y
    
    Example:
        >>> agent = MyAgent(llm)
        >>> action = agent.step(state)
    """
```

### 9. Handle Rate Limits

```python
from openhands.llm import LLM

# LLM handles rate limiting automatically
response = self.llm.completion_with_retries(
    messages=messages,
    temperature=0.0,
)
```

### 10. Monitor Metrics

```python
def step(self, state: State) -> Action:
    # Update metrics
    state.local_metrics.steps += 1
    
    # Check cost limits
    if state.global_metrics.accumulated_cost > MAX_COST:
        return AgentFinishAction(
            outputs={"reason": "Cost limit exceeded"}
        )
```

---

## Testing Agents

### Unit Tests

```python
import pytest
from openhands.agenthub.my_agent.agent import MyAgent
from openhands.controller.state.state import State

def test_agent_initialization():
    from unittest.mock import MagicMock
    llm = MagicMock()
    agent = MyAgent(llm)
    assert agent.llm == llm

def test_agent_step():
    from unittest.mock import MagicMock
    llm = MagicMock()
    agent = MyAgent(llm)
    
    state = State(inputs={}, iteration=0)
    action = agent.step(state)
    
    assert action is not None
```

### Integration Tests

```python
@pytest.mark.integration
async def test_agent_with_runtime():
    """Test agent with actual runtime."""
    from openhands.runtime import DockerRuntime
    
    runtime = DockerRuntime()
    agent = MyAgent(llm)
    
    # Execute agent
    state = State(inputs={}, iteration=0)
    action = agent.step(state)
    
    # Execute action in runtime
    observation = await runtime.execute(action)
    
    assert observation is not None
```

---

## Advanced Topics

### Custom Memory Management

```python
class MyAgent(Agent):
    def build_messages(self, state: State) -> list:
        """Custom memory management."""
        # Only include last N events
        recent_history = state.history[-10:]
        
        messages = [{"role": "system", "content": self.system_prompt()}]
        for event in recent_history:
            messages.append(self.event_to_message(event))
        
        return messages
```

### Streaming Responses

```python
def step(self, state: State) -> Action:
    """Stream LLM responses."""
    response = self.llm.completion(
        messages=self.build_messages(state),
        stream=True,
    )
    
    content = ""
    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        content += delta
        # Optionally send partial updates
    
    return self.parse_response_content(content)
```

### Multi-turn Conversations

```python
def step(self, state: State) -> Action:
    """Handle multi-turn conversations."""
    if self.needs_clarification(state):
        return MessageAction(
            content="Could you provide more details about X?",
            wait_for_response=True,
        )
    
    # Continue with task
    return self.execute_task(state)
```

---

For more details on:
- LLM integration: See [../llm/AGENTS.md](../llm/AGENTS.md)
- Runtime execution: See [../runtime/AGENTS.md](../runtime/AGENTS.md)
- Backend development: See [../AGENTS.md](../AGENTS.md)
