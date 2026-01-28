# Runtime Development Guide (openhands/runtime/)

This guide provides detailed information for working with and implementing runtimes in OpenHands.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Using Runtimes](#using-runtimes)
4. [Implementing a Runtime](#implementing-a-runtime)
5. [Action Execution Server](#action-execution-server)
6. [Plugins](#plugins)
7. [Best Practices](#best-practices)

---

## Overview

Runtimes provide sandboxed execution environments where agents can:
- Run bash commands
- Execute Python code (via Jupyter)
- Read and write files
- Browse the web
- Use MCP (Model Context Protocol) servers

**Available runtime types:**
- **Local Runtime**: Executes on the local machine
- **Docker Runtime**: Containerized execution (default)
- **E2B Runtime**: Cloud-based sandboxes
- **Modal Runtime**: Scalable cloud execution
- **Remote Runtime**: Custom remote sandboxes
- **Kubernetes Runtime**: Cluster-based execution
- **Runloop Runtime**: Runloop-based sandboxes
- **Daytona Runtime**: Daytona workspace integration

---

## Architecture

```
┌─────────────────────────────────────┐
│   Agent                             │
├─────────────────────────────────────┤
│   Action Execution Client           │ ← Agent-side client
├─────────────────────────────────────┤
│   HTTP/WebSocket                    │ ← Communication
├─────────────────────────────────────┤
│   Action Execution Server           │ ← REST API in sandbox
├─────────────────────────────────────┤
│   Plugins (Jupyter, MCP, etc.)      │ ← Extensions
├─────────────────────────────────────┤
│   Sandbox Environment               │ ← Isolated execution
└─────────────────────────────────────┘
```

**Key components:**
- **Runtime**: Manages sandbox lifecycle
- **Action Execution Server**: REST API for executing actions
- **Plugins**: Extend runtime capabilities
- **Runtime Builder**: Builds Docker images

---

## Using Runtimes

### Creating a Runtime

```python
from openhands.runtime import create_runtime
from openhands.core.config import AppConfig

# Create config
config = AppConfig()

# Create runtime
runtime = create_runtime(config)

# Initialize runtime
await runtime.connect()
```

### Executing Actions

```python
from openhands.events.action import CmdRunAction

# Create action
action = CmdRunAction(command="ls -la")

# Execute action
observation = await runtime.run_action(action)

# Get result
print(observation.content)
```

### Reading Files

```python
from openhands.events.action import FileReadAction

action = FileReadAction(path="/path/to/file.py")
observation = await runtime.run_action(action)

print(observation.content)  # File contents
```

### Writing Files

```python
from openhands.events.action import FileWriteAction

action = FileWriteAction(
    path="/path/to/file.py",
    content="print('Hello, World!')"
)
observation = await runtime.run_action(action)
```

### Running Python Code

```python
from openhands.events.action import IPythonRunCellAction

action = IPythonRunCellAction(
    code="""
import numpy as np
result = np.array([1, 2, 3]).mean()
print(f"Mean: {result}")
"""
)
observation = await runtime.run_action(action)
```

### Browsing the Web

```python
from openhands.events.action import BrowseURLAction

action = BrowseURLAction(url="https://example.com")
observation = await runtime.run_action(action)

print(observation.content)  # Page content
```

---

## Implementing a Runtime

### Step 1: Create Runtime Class

Implement the `Runtime` interface from `openhands/runtime/base.py`:

```python
from openhands.runtime.base import Runtime
from openhands.events.action import Action
from openhands.events.observation import Observation

class MyRuntime(Runtime):
    """Custom runtime implementation."""

    def __init__(self, config, event_stream):
        """Initialize runtime."""
        super().__init__(config, event_stream)
        # Custom initialization

    async def connect(self):
        """Connect to or create the sandbox."""
        # Set up sandbox environment
        # Start action execution server
        self.action_execution_server_url = "http://..."

    async def run_action(self, action: Action) -> Observation:
        """Execute an action in the sandbox."""
        # Send action to execution server
        # Return observation
        pass

    async def close(self):
        """Clean up runtime resources."""
        # Stop sandbox
        # Clean up resources
        pass

    async def copy_to(
        self,
        host_src: str,
        sandbox_dest: str,
        recursive: bool = False,
    ):
        """Copy files from host to sandbox."""
        pass

    async def copy_from(
        self,
        sandbox_src: str,
        host_dest: str,
        recursive: bool = False,
    ):
        """Copy files from sandbox to host."""
        pass

    async def list_files(self, path: str = "/") -> list[str]:
        """List files in sandbox."""
        pass

    async def read_file(self, path: str) -> str:
        """Read file from sandbox."""
        pass

    async def write_file(self, path: str, content: str):
        """Write file to sandbox."""
        pass
```

### Step 2: Implement Connection Logic

```python
async def connect(self):
    """Connect to or create the sandbox."""
    # Example: Docker container
    import docker

    client = docker.from_env()

    # Create container
    self.container = client.containers.run(
        image="openhands-runtime:latest",
        detach=True,
        ports={'3000/tcp': None},  # Action execution server port
        volumes={
            self.config.workspace_dir: {
                'bind': '/workspace',
                'mode': 'rw',
            }
        },
    )

    # Wait for action execution server to start
    await self.wait_for_server()

    # Get server URL
    port = self.container.attrs['NetworkSettings']['Ports']['3000/tcp'][0]['HostPort']
    self.action_execution_server_url = f"http://localhost:{port}"
```

### Step 3: Implement Action Execution

```python
async def run_action(self, action: Action) -> Observation:
    """Execute an action in the sandbox."""
    import aiohttp

    # Serialize action
    action_dict = action.to_dict()

    # Send to action execution server
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.action_execution_server_url}/execute",
            json=action_dict,
        ) as response:
            result = await response.json()

    # Deserialize observation
    from openhands.events.serialization import observation_from_dict
    observation = observation_from_dict(result)

    return observation
```

### Step 4: Register Runtime

Add to `openhands/runtime/__init__.py`:

```python
from .my_runtime import MyRuntime

RUNTIME_CLASSES = {
    'local': LocalRuntime,
    'docker': DockerRuntime,
    'my_runtime': MyRuntime,  # Add your runtime
}

def create_runtime(config, event_stream=None):
    runtime_type = config.runtime
    runtime_class = RUNTIME_CLASSES.get(runtime_type)

    if not runtime_class:
        raise ValueError(f"Unknown runtime type: {runtime_type}")

    return runtime_class(config, event_stream)
```

### Step 5: Add Tests

```python
# tests/unit/runtime/test_my_runtime.py
import pytest
from openhands.runtime.my_runtime import MyRuntime
from openhands.events.action import CmdRunAction

@pytest.mark.asyncio
async def test_my_runtime():
    """Test custom runtime."""
    config = AppConfig(runtime="my_runtime")
    runtime = MyRuntime(config, None)

    await runtime.connect()

    # Test command execution
    action = CmdRunAction(command="echo 'hello'")
    observation = await runtime.run_action(action)

    assert "hello" in observation.content

    await runtime.close()
```

---

## Action Execution Server

The Action Execution Server is a REST API that runs inside the sandbox and executes agent actions.

### Server Structure

```python
from fastapi import FastAPI, HTTPException
from openhands.events.action import Action
from openhands.events.observation import Observation
from openhands.events.serialization import action_from_dict

app = FastAPI()

@app.post("/execute")
async def execute_action(action_dict: dict) -> dict:
    """Execute an action and return observation."""
    try:
        # Deserialize action
        action = action_from_dict(action_dict)

        # Execute action
        observation = await execute(action)

        # Serialize observation
        return observation.to_dict()
    except Exception as e:
        return ErrorObservation(content=str(e)).to_dict()

async def execute(action: Action) -> Observation:
    """Execute action based on type."""
    if isinstance(action, CmdRunAction):
        return await execute_command(action)
    elif isinstance(action, FileReadAction):
        return await execute_file_read(action)
    elif isinstance(action, FileWriteAction):
        return await execute_file_write(action)
    else:
        raise ValueError(f"Unknown action type: {type(action)}")
```

### Command Execution

```python
async def execute_command(action: CmdRunAction) -> CmdOutputObservation:
    """Execute bash command."""
    import subprocess

    try:
        result = subprocess.run(
            action.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )

        return CmdOutputObservation(
            content=result.stdout,
            command=action.command,
            exit_code=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return ErrorObservation(
            content="Command timeout",
        )
```

### File Operations

```python
async def execute_file_read(action: FileReadAction) -> FileReadObservation:
    """Read file."""
    try:
        with open(action.path, 'r') as f:
            content = f.read()

        return FileReadObservation(
            content=content,
            path=action.path,
        )
    except FileNotFoundError:
        return ErrorObservation(
            content=f"File not found: {action.path}",
        )

async def execute_file_write(action: FileWriteAction) -> FileWriteObservation:
    """Write file."""
    try:
        # Create parent directories
        os.makedirs(os.path.dirname(action.path), exist_ok=True)

        with open(action.path, 'w') as f:
            f.write(action.content)

        return FileWriteObservation(
            content="File written successfully",
            path=action.path,
        )
    except Exception as e:
        return ErrorObservation(
            content=f"Failed to write file: {e}",
        )
```

---

## Plugins

Plugins extend runtime capabilities.

### Available Plugins

**Jupyter Plugin:**
- Enables IPython code execution
- Maintains Python interpreter state
- Supports interactive computing

**MCP Plugin:**
- Model Context Protocol integration
- Connects to MCP servers
- Extends agent capabilities

**Browser Plugin:**
- Web browsing capabilities
- Playwright/Selenium integration
- Screenshot and PDF generation

**VSCode Plugin:**
- VSCode extension integration
- IDE-based development

### Implementing a Plugin

```python
from openhands.runtime.plugins.plugin import Plugin

class MyPlugin(Plugin):
    """Custom plugin implementation."""

    def __init__(self, config):
        """Initialize plugin."""
        super().__init__(config)
        # Custom initialization

    async def initialize(self, runtime):
        """Initialize plugin in runtime."""
        # Set up plugin resources
        # Install dependencies
        # Configure environment
        pass

    async def execute(self, action: Action) -> Observation:
        """Execute plugin-specific action."""
        # Handle plugin actions
        pass

    async def cleanup(self):
        """Clean up plugin resources."""
        # Stop services
        # Clean up files
        pass
```

### Registering a Plugin

```python
from openhands.runtime.plugins import PluginManager

# Create plugin manager
plugin_manager = PluginManager(config)

# Register plugin
plugin_manager.register('my_plugin', MyPlugin)

# Initialize plugins
await plugin_manager.initialize_all(runtime)
```

### Using Plugins

```python
# In runtime
class MyRuntime(Runtime):
    async def connect(self):
        """Connect and initialize plugins."""
        # Connect to sandbox
        await super().connect()

        # Initialize plugins
        self.plugin_manager = PluginManager(self.config)
        await self.plugin_manager.initialize_all(self)

    async def run_action(self, action: Action) -> Observation:
        """Execute action, using plugins if needed."""
        # Check if plugin can handle action
        if self.plugin_manager.can_handle(action):
            return await self.plugin_manager.execute(action)

        # Otherwise, use default execution
        return await super().run_action(action)
```

---

## Best Practices

### 1. Resource Management

```python
async def connect(self):
    """Always clean up resources."""
    try:
        # Create sandbox
        self.sandbox = await create_sandbox()
    except Exception as e:
        # Clean up on failure
        await self.cleanup()
        raise

async def close(self):
    """Clean up all resources."""
    try:
        if self.sandbox:
            await self.sandbox.stop()
    finally:
        # Ensure cleanup happens
        await self.cleanup_temp_files()
```

### 2. Error Handling

```python
async def run_action(self, action: Action) -> Observation:
    """Always return an observation, even on error."""
    try:
        return await self.execute_action(action)
    except Exception as e:
        return ErrorObservation(
            content=f"Runtime error: {str(e)}",
        )
```

### 3. Timeout Management

```python
import asyncio

async def run_action(self, action: Action) -> Observation:
    """Use timeouts for all operations."""
    try:
        return await asyncio.wait_for(
            self.execute_action(action),
            timeout=300.0,  # 5 minutes
        )
    except asyncio.TimeoutError:
        return ErrorObservation(
            content="Action timed out",
        )
```

### 4. Workspace Isolation

```python
async def connect(self):
    """Isolate workspace directories."""
    # Create unique workspace for this runtime
    self.workspace_dir = f"/tmp/openhands-{self.id}"
    os.makedirs(self.workspace_dir, exist_ok=True)

    # Mount to sandbox
    self.mount_workspace(self.workspace_dir)
```

### 5. Security

```python
async def run_action(self, action: Action) -> Observation:
    """Validate and sanitize all inputs."""
    # Validate path
    if isinstance(action, FileReadAction):
        if not self.is_safe_path(action.path):
            return ErrorObservation(
                content="Invalid path",
            )

    # Validate command
    if isinstance(action, CmdRunAction):
        if self.is_dangerous_command(action.command):
            return ErrorObservation(
                content="Dangerous command blocked",
            )

    return await self.execute_action(action)

def is_safe_path(self, path: str) -> bool:
    """Check if path is within workspace."""
    abs_path = os.path.abspath(path)
    return abs_path.startswith(self.workspace_dir)
```

### 6. Logging

```python
import logging

logger = logging.getLogger(__name__)

async def run_action(self, action: Action) -> Observation:
    """Log all runtime operations."""
    logger.info(
        "Executing action",
        extra={
            "action_type": type(action).__name__,
            "runtime_id": self.id,
        }
    )

    try:
        observation = await self.execute_action(action)
        logger.info(
            "Action completed",
            extra={
                "observation_type": type(observation).__name__,
            }
        )
        return observation
    except Exception as e:
        logger.error(
            "Action failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise
```

### 7. Health Checks

```python
async def health_check(self) -> bool:
    """Check runtime health."""
    try:
        # Ping action execution server
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.action_execution_server_url}/health"
            ) as response:
                return response.status == 200
    except Exception:
        return False
```

### 8. State Persistence

```python
async def save_state(self):
    """Save runtime state for recovery."""
    state = {
        'workspace_dir': self.workspace_dir,
        'sandbox_id': self.sandbox_id,
        'plugins': self.plugin_manager.get_state(),
    }

    with open(self.state_file, 'w') as f:
        json.dump(state, f)

async def restore_state(self):
    """Restore runtime from saved state."""
    with open(self.state_file, 'r') as f:
        state = json.load(f)

    self.workspace_dir = state['workspace_dir']
    self.sandbox_id = state['sandbox_id']
    await self.plugin_manager.restore_state(state['plugins'])
```

### 9. Monitoring

```python
from openhands.runtime.metrics import RuntimeMetrics

async def run_action(self, action: Action) -> Observation:
    """Track runtime metrics."""
    start_time = time.time()

    try:
        observation = await self.execute_action(action)

        # Record success metric
        self.metrics.record_action(
            action_type=type(action).__name__,
            duration=time.time() - start_time,
            success=True,
        )

        return observation
    except Exception as e:
        # Record failure metric
        self.metrics.record_action(
            action_type=type(action).__name__,
            duration=time.time() - start_time,
            success=False,
            error=str(e),
        )
        raise
```

### 10. Testing

```python
@pytest.mark.asyncio
async def test_runtime_lifecycle():
    """Test runtime lifecycle."""
    runtime = MyRuntime(config, None)

    # Test connection
    await runtime.connect()
    assert await runtime.health_check()

    # Test action execution
    action = CmdRunAction(command="echo test")
    observation = await runtime.run_action(action)
    assert "test" in observation.content

    # Test cleanup
    await runtime.close()
    assert not await runtime.health_check()
```

---

## Troubleshooting

### Sandbox Won't Start
- Check Docker daemon is running
- Verify image exists
- Check port conflicts
- Review container logs

### Actions Timing Out
- Increase timeout values
- Check network connectivity
- Verify action execution server is running
- Review server logs

### File Permission Issues
- Check volume mount permissions
- Verify user/group IDs match
- Use appropriate file modes
- Test with simpler permissions first

### Plugin Failures
- Check plugin dependencies installed
- Verify plugin initialization succeeded
- Review plugin logs
- Test plugin independently

### Memory Issues
- Monitor container memory usage
- Set memory limits appropriately
- Clean up temporary files
- Use streaming for large files

---

For agent development, see [../agenthub/AGENTS.md](../agenthub/AGENTS.md).
For backend development, see [../AGENTS.md](../AGENTS.md).
For general guidelines, see [../../AGENTS.md](../../AGENTS.md).
