# AGENTS.md - OpenHands Coding Agent Guide

Welcome! This document provides comprehensive guidance for AI coding agents working on the OpenHands codebase.

## 📖 Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Architecture](#repository-architecture)
3. [General Setup](#general-setup)
4. [Development Workflow](#development-workflow)
5. [Testing Strategy](#testing-strategy)
6. [Key Components](#key-components)
7. [Module-Specific Guides](#module-specific-guides)

---

## Project Overview

This repository contains **OpenHands**, an automated AI software engineer platform. It consists of:

- **Python Backend** (in `openhands/`) - Core agent logic, LLM integration, runtime management
- **React Frontend** (in `frontend/`) - User interface and API client
- **Enterprise Edition** (in `enterprise/`) - Additional features for enterprise customers
- **VSCode Extension** (in `openhands/integrations/vscode/`) - IDE integration

**Key Technologies:**
- Backend: Python 3.12+, FastAPI, Poetry, asyncio
- Frontend: React, TypeScript, TanStack Query, Vite, Tailwind CSS
- Runtime: Docker, Kubernetes, various sandbox providers
- Testing: pytest (backend), vitest (frontend)

---

## Repository Architecture

```
OpenHands/
├── openhands/              # Backend Python code
│   ├── agenthub/          # Agent implementations
│   ├── controller/        # Agent control loop and state management
│   ├── llm/              # LLM integration (LiteLLM wrapper)
│   ├── runtime/          # Sandbox execution environments
│   ├── events/           # Action and Observation types
│   ├── server/           # FastAPI backend server
│   ├── storage/          # Database models and persistence
│   └── ...
├── frontend/              # React frontend
│   ├── src/
│   │   ├── api/          # API client methods (Data Access Layer)
│   │   ├── hooks/        # TanStack Query hooks
│   │   ├── components/   # React components
│   │   ├── routes/       # Page components
│   │   └── ...
│   └── ...
├── enterprise/            # Enterprise-only features
│   ├── server/           # Enterprise server extensions
│   ├── integrations/     # GitHub, GitLab, Jira, Linear, Slack
│   ├── storage/          # Enterprise database models
│   └── migrations/       # Alembic database migrations
├── tests/                 # Test suites
│   ├── unit/             # Unit tests
│   ├── runtime/          # Runtime integration tests
│   └── e2e/              # End-to-end tests
├── .openhands/           # Repository-specific configuration
│   └── microagents/      # Repo-specific microagents
└── ...
```

---

## General Setup

### Initial Setup
To set up the entire repo, including frontend and backend, run:
```bash
make build
```
You don't need to do this unless the user asks you to, or if you're trying to run the entire application.

### Running OpenHands with OpenHands

You can run the full application to debug issues or test changes:
To run the full application to debug issues:
```bash
export INSTALL_DOCKER=0
export RUNTIME=local
make build && make run FRONTEND_PORT=12000 FRONTEND_HOST=0.0.0.0 BACKEND_HOST=0.0.0.0 &> /tmp/openhands-log.txt &
```

---

## Development Workflow

### Pre-commit Hooks (MANDATORY)

**IMPORTANT**: Before making any changes to the codebase, ALWAYS run:
```bash
make install-pre-commit-hooks
```
This ensures pre-commit hooks are properly installed.

### Linting and Code Quality

Before pushing any changes, you MUST ensure that any lint errors or simple test errors have been fixed.

**Backend changes:**
```bash
pre-commit run --config ./dev_config/python/.pre-commit-config.yaml
```
This will run on staged files and check:
- Mypy type checking
- Ruff formatting and linting
- Trailing whitespace
- Missing newlines at end of files

**Frontend changes:**
```bash
cd frontend && npm run lint:fix && npm run build ; cd ..
```

**VSCode extension changes:**
```bash
cd openhands/integrations/vscode && npm run lint:fix && npm run compile ; cd ../../..
```

The pre-commit hooks MUST pass successfully before pushing any changes to the repository. This is a mandatory requirement to maintain code quality and consistency.

If either command fails, it may have automatically fixed some issues. You should fix any issues that weren't automatically fixed, then re-run the command to ensure it passes.

### Git Best Practices

- **Specific staging**: Prefer `git add <filename>` instead of `git add .` to avoid accidentally staging unintended files
- **Careful resets**: Be especially careful with `git reset --hard` after staging files, as it will remove accidentally staged files
- **Rebasing**: When remote has new changes, use `git fetch upstream && git rebase upstream/<branch>` on the same branch
- **Git commands**: Use `git --no-pager` for commands like `git status`, `git diff`, etc. to avoid pagination issues

---

## Testing Strategy

### Backend Testing (pytest)

**Location**: All tests are in `tests/unit/test_*.py`

**Running tests:**
```bash
# Run specific test file
poetry run pytest tests/unit/test_xxx.py

# Run with coverage
poetry run pytest tests/unit/ --cov=openhands --cov-report=term-missing

# Run specific test function
poetry run pytest tests/unit/test_xxx.py::test_function_name
```

**Test structure:**
- Use pytest fixtures for setup/teardown
- Mock external dependencies
- Test both success and failure scenarios
- Aim for 90%+ coverage on new code

### Frontend Testing (vitest)

**Location**: Tests are co-located with source files or in `__tests__` directories

**Running tests:**
```bash
cd frontend

# Run all tests
npm run test

# Run specific tests
npm run test -- -t "TestName"

# Run in watch mode
npm run test -- --watch
```

**Test patterns:**
- Use React Testing Library for component tests
- Mock API calls with MSW (Mock Service Worker)
- Test user interactions and edge cases
- Keep tests fast and focused

### Enterprise Testing

**Running enterprise tests:**
```bash
# Full suite
PYTHONPATH=".:$PYTHONPATH" poetry run --project=enterprise pytest --forked -n auto -s ./enterprise/tests/unit --cov=enterprise --cov-branch

# Specific module
cd enterprise
PYTHONPATH=".:$PYTHONPATH" poetry run pytest tests/unit/telemetry/ --confcutdir=tests/unit/telemetry

# Linting (IMPORTANT: use --show-diff-on-failure to match GitHub CI)
poetry run pre-commit run --all-files --show-diff-on-failure --config ./dev_config/python/.pre-commit-config.yaml
```

**Enterprise testing best practices:**
- Use SQLite in-memory databases (`sqlite:///:memory:`) for unit tests
- Mock external dependencies (databases, APIs, file systems)
- Use relative imports without `enterprise.` prefix
- Write platform-agnostic tests

---

## Key Components

### Agents (openhands/agenthub/)

Agents are the core AI entities that perform software development tasks. Each agent implements a `step()` method that takes a `State` and returns an `Action`.

**Main agents:**
- **CodeActAgent**: Primary agent that writes and executes code
- **BrowsingAgent**: Specialized for web browsing tasks
- **DummyAgent**: Simple agent for testing
- **ReadOnlyAgent**: Agent with read-only permissions

**Creating an agent:**
1. Extend the `Agent` base class
2. Implement `step(state: State) -> Action` method
3. Use `self.llm` to interact with language models
4. Return appropriate `Action` objects

See [openhands/agenthub/AGENTS.md](openhands/agenthub/AGENTS.md) for detailed agent development guide.

### LLM Integration (openhands/llm/)

The LLM module wraps LiteLLM and provides:
- Model management and configuration
- Streaming responses
- Function calling support
- Prompt caching
- Rate limiting and retry logic

**Key files:**
- `llm.py`: Main LLM class and model features
- `llm_registry.py`: Model registry and provider management
- `metrics.py`: LLM usage metrics

See [openhands/llm/AGENTS.md](openhands/llm/AGENTS.md) for LLM integration guide.

### Runtime (openhands/runtime/)

Runtimes provide sandboxed execution environments for agents to run code and commands.

**Runtime types:**
- **Local Runtime**: Executes on the local machine
- **Docker Runtime**: Containerized execution (default)
- **E2B Runtime**: Cloud-based sandboxes
- **Modal Runtime**: Scalable cloud execution
- **Kubernetes Runtime**: Cluster-based execution

**Key concepts:**
- **Action Execution Server**: REST API that executes agent actions
- **Runtime Builder**: Builds Docker images from user-specified base images
- **Plugins**: Extend runtime capabilities (e.g., Jupyter, MCP servers)

See [openhands/runtime/AGENTS.md](openhands/runtime/AGENTS.md) for runtime implementation guide.

### Events System (openhands/events/)

Events are the building blocks of agent-user interactions.

**Event types:**
1. **Actions**: Operations initiated by agents
   - `CmdRunAction`: Run bash commands
   - `IPythonRunCellAction`: Execute Python code
   - `FileReadAction`, `FileWriteAction`: File operations
   - `BrowseURLAction`: Web browsing
   - `AgentFinishAction`: Complete task

2. **Observations**: Results returned after actions
   - `CmdOutputObservation`: Command output
   - `FileReadObservation`: File contents
   - `ErrorObservation`: Error messages
   - `SuccessObservation`: Success confirmations

**Serialization:**
- `action.to_dict()`: Serialize for UI
- `action.to_memory()`: Serialize for LLM (includes raw details)
- `action_from_dict()`: Deserialize from dict

### Controller (openhands/controller/)

The controller manages the agent lifecycle and orchestrates the interaction loop.

**Key components:**
- `AgentController`: Main control loop
- `State`: Agent state management (history, metrics, delegates)
- `action_parser.py`: Parses LLM responses into actions

**Agent delegation:**
- Agents can delegate tasks to specialized agents
- Each subtask has its own local iteration counter
- Global iteration counter tracks overall progress

---

## Module-Specific Guides

For detailed guidance on specific modules, refer to:

- **[openhands/AGENTS.md](openhands/AGENTS.md)** - Backend Python development
- **[frontend/AGENTS.md](frontend/AGENTS.md)** - Frontend React development
- **[enterprise/AGENTS.md](enterprise/AGENTS.md)** - Enterprise features
- **[openhands/agenthub/AGENTS.md](openhands/agenthub/AGENTS.md)** - Agent development
- **[openhands/llm/AGENTS.md](openhands/llm/AGENTS.md)** - LLM integration
- **[openhands/runtime/AGENTS.md](openhands/runtime/AGENTS.md)** - Runtime implementation
- **[tests/AGENTS.md](tests/AGENTS.md)** - Testing guidelines

---

## Backend Details (openhands/)

- Located in the `openhands` directory
- Testing:
  - All tests are in `tests/unit/test_*.py`
  - To test new code, run `poetry run pytest tests/unit/test_xxx.py` where `xxx` is the appropriate file for the current functionality
  - Write all tests with pytest

See [openhands/AGENTS.md](openhands/AGENTS.md) for detailed backend development guide.

---

## Frontend Details (frontend/)

- Located in the `frontend` directory
- Prerequisites: Node.js 22.x or later, npm
- Setup: Run `npm install` in the frontend directory

**Testing:**
- Run tests: `npm run test`
- To run specific tests: `npm run test -- -t "TestName"`
- Our test framework is vitest

**Building:**
- Build for production: `npm run build`

**Environment Variables:**
- Set in `frontend/.env` or as environment variables
- Available variables: `VITE_BACKEND_HOST`, `VITE_USE_TLS`, `VITE_INSECURE_SKIP_VERIFY`, `VITE_FRONTEND_PORT`

**Internationalization:**
- Generate i18n declaration file: `npm run make-i18n`

**Data Fetching & Cache Management:**
- We use TanStack Query (fka React Query) for data fetching and cache management
- Data Access Layer: API client methods are located in `frontend/src/api` and should never be called directly from UI components - they must always be wrapped with TanStack Query
- Custom hooks are located in `frontend/src/hooks/query/` and `frontend/src/hooks/mutation/`
- Query hooks should follow the pattern `use[Resource]` (e.g., `useConversationSkills`)
- Mutation hooks should follow the pattern `use[Action]` (e.g., `useDeleteConversation`)
- Architecture rule: UI components → TanStack Query hooks → Data Access Layer (`frontend/src/api`) → API endpoints

See [frontend/AGENTS.md](frontend/AGENTS.md) for detailed frontend development guide.

---

## VSCode Extension (openhands/integrations/vscode/)


- Located in the `openhands/integrations/vscode` directory
- Setup: Run `npm install` in the extension directory
- Linting:
  - Run linting with fixes: `npm run lint:fix`
  - Check only: `npm run lint`
  - Type checking: `npm run typecheck`
- Building:
  - Compile TypeScript: `npm run compile`
  - Package extension: `npm run package-vsix`
- Testing:
  - Run tests: `npm run test`
- Development Best Practices:
  - Use `vscode.window.createOutputChannel()` for debug logging instead of `showErrorMessage()` popups
  - Pre-commit process runs both frontend and backend checks when committing extension changes

## Enterprise Directory

The `enterprise/` directory contains additional functionality that extends the open-source OpenHands codebase. This includes:
- Authentication and user management (Keycloak integration)
- Database migrations (Alembic)
- Integration services (GitHub, GitLab, Jira, Linear, Slack)
- Billing and subscription management (Stripe)
- Telemetry and analytics (PostHog, custom metrics framework)

### Enterprise Development Setup

**Prerequisites:**
- Python 3.12
- Poetry (for dependency management)
- Node.js 22.x (for frontend)
- Docker (optional)

**Setup Steps:**
1. First, build the main OpenHands project: `make build`
2. Then install enterprise dependencies: `cd enterprise && poetry install --with dev,test` (This can take a very long time. Be patient.)
3. Set up enterprise pre-commit hooks: `poetry run pre-commit install --config ./dev_config/python/.pre-commit-config.yaml`

**Running Enterprise Tests:**
```bash
# Enterprise unit tests (full suite)
PYTHONPATH=".:$PYTHONPATH" poetry run --project=enterprise pytest --forked -n auto -s -p no:ddtrace -p no:ddtrace.pytest_bdd -p no:ddtrace.pytest_benchmark ./enterprise/tests/unit --cov=enterprise --cov-branch

# Test specific modules (faster for development)
cd enterprise
PYTHONPATH=".:$PYTHONPATH" poetry run pytest tests/unit/telemetry/ --confcutdir=tests/unit/telemetry

# Enterprise linting (IMPORTANT: use --show-diff-on-failure to match GitHub CI)
poetry run pre-commit run --all-files --show-diff-on-failure --config ./dev_config/python/.pre-commit-config.yaml
```

**Running Enterprise Server:**
```bash
cd enterprise
make start-backend  # Development mode with hot reload
# or
make run  # Full application (backend + frontend)
```

**Key Configuration Files:**
- `enterprise/pyproject.toml` - Enterprise-specific dependencies
- `enterprise/Makefile` - Enterprise build and run commands
- `enterprise/dev_config/python/` - Linting and type checking configuration
- `enterprise/migrations/` - Database migration files

**Database Migrations:**
Enterprise uses Alembic for database migrations. When making schema changes:
1. Create migration files in `enterprise/migrations/versions/`
2. Test migrations thoroughly
3. The CI will check for migration conflicts on PRs

**Integration Development:**
The enterprise codebase includes integrations for:
- **GitHub** - PR management, webhooks, app installations
- **GitLab** - Similar to GitHub but for GitLab instances
- **Jira** - Issue tracking and project management
- **Linear** - Modern issue tracking
- **Slack** - Team communication and notifications

Each integration follows a consistent pattern with service classes, storage models, and API endpoints.

**Important Notes:**
- Enterprise code is licensed under Polyform Free Trial License (30-day limit)
- The enterprise server extends the OpenHands server through dynamic imports
- Database changes require careful migration planning in `enterprise/migrations/`
- Always test changes in both OpenHands and enterprise contexts
- Use the enterprise-specific Makefile commands for development

**Enterprise Testing Best Practices:**

**Database Testing:**
- Use SQLite in-memory databases (`sqlite:///:memory:`) for unit tests instead of real PostgreSQL
- Create module-specific `conftest.py` files with database fixtures
- Mock external database connections in unit tests to avoid dependency on running services
- Use real database connections only for integration tests

**Import Patterns:**
- Use relative imports without `enterprise.` prefix in enterprise code
- Example: `from storage.database import session_maker` not `from enterprise.storage.database import session_maker`
- This ensures code works in both OpenHands and enterprise contexts

**Test Structure:**
- Place tests in `enterprise/tests/unit/` following the same structure as the source code
- Use `--confcutdir=tests/unit/[module]` when testing specific modules
- Create comprehensive fixtures for complex objects (databases, external services)
- Write platform-agnostic tests (avoid hardcoded OS-specific assertions)

**Mocking Strategy:**
- Use `AsyncMock` for async operations and `MagicMock` for complex objects
- Mock all external dependencies (databases, APIs, file systems) in unit tests
- Use `patch` with correct import paths (e.g., `telemetry.registry.logger` not `enterprise.telemetry.registry.logger`)
- Test both success and failure scenarios with proper error handling

**Coverage Goals:**
- Aim for 90%+ test coverage on new enterprise modules
- Focus on critical business logic and error handling paths
- Use `--cov-report=term-missing` to identify uncovered lines

**Troubleshooting:**
- If tests fail, ensure all dependencies are installed: `poetry install --with dev,test`
- For database issues, check migration status and run migrations if needed
- For frontend issues, ensure the main OpenHands frontend is built: `make build`
- Check logs in the `logs/` directory for runtime issues
- If tests fail with import errors, verify `PYTHONPATH=".:$PYTHONPATH"` is set
- **If GitHub CI fails but local linting passes**: Always use `--show-diff-on-failure` flag to match CI behavior exactly

## Template for Github Pull Request

If you are starting a pull request (PR), please follow the template in `.github/pull_request_template.md`.

## Implementation Details

These details may or may not be useful for your current task.

### Microagents

Microagents are specialized prompts that enhance OpenHands with domain-specific knowledge and task-specific workflows. They are Markdown files that can include frontmatter for configuration.

#### Types:
- **Public Microagents**: Located in `microagents/`, available to all users
- **Repository Microagents**: Located in `.openhands/microagents/`, specific to this repository

#### Loading Behavior:
- **Without frontmatter**: Always loaded into LLM context
- **With triggers in frontmatter**: Only loaded when user's message matches the specified trigger keywords

#### Structure:
```yaml
---
triggers:
- keyword1
- keyword2
---
# Microagent Content
Your specialized knowledge and instructions here...
```

### Frontend

#### Action Handling:
- Actions are defined in `frontend/src/types/action-type.ts`
- The `HANDLED_ACTIONS` array in `frontend/src/state/chat-slice.ts` determines which actions are displayed as collapsible UI elements
- To add a new action type to the UI:
  1. Add the action type to the `HANDLED_ACTIONS` array
  2. Implement the action handling in `addAssistantAction` function in chat-slice.ts
  3. Add a translation key in the format `ACTION_MESSAGE$ACTION_NAME` to the i18n files
- Actions with `thought` property are displayed in the UI based on their action type:
  - Regular actions (like "run", "edit") display the thought as a separate message
  - Special actions (like "think") are displayed as collapsible elements only

#### Adding User Settings:
- To add a new user setting to OpenHands, follow these steps:
  1. Add the setting to the frontend:
     - Add the setting to the `Settings` type in `frontend/src/types/settings.ts`
     - Add the setting to the `ApiSettings` type in the same file
     - Add the setting with an appropriate default value to `DEFAULT_SETTINGS` in `frontend/src/services/settings.ts`
     - Update the `useSettings` hook in `frontend/src/hooks/query/use-settings.ts` to map the API response
     - Update the `useSaveSettings` hook in `frontend/src/hooks/mutation/use-save-settings.ts` to include the setting in API requests
     - Add UI components (like toggle switches) in the appropriate settings screen (e.g., `frontend/src/routes/app-settings.tsx`)
     - Add i18n translations for the setting name and any tooltips in `frontend/src/i18n/translation.json`
     - Add the translation key to `frontend/src/i18n/declaration.ts`
  2. Add the setting to the backend:
     - Add the setting to the `Settings` model in `openhands/storage/data_models/settings.py`
     - Update any relevant backend code to apply the setting (e.g., in session creation)

#### Settings UI Patterns:

There are two main patterns for saving settings in the OpenHands frontend:

**Pattern 1: Entity-based Resources (Immediate Save)**
- Used for: API Keys, Secrets, MCP Servers
- Behavior: Changes are saved immediately when user performs actions (add/edit/delete)
- Implementation:
  - No "Save Changes" button
  - No local state management or `isDirty` tracking
  - Uses dedicated mutation hooks for each operation (e.g., `use-add-mcp-server.ts`, `use-delete-mcp-server.ts`)
  - Each mutation triggers immediate API call with query invalidation for UI updates
  - Example: MCP settings, API Keys & Secrets tabs
- Benefits: Simpler UX, no risk of losing changes, consistent with modern web app patterns

**Pattern 2: Form-based Settings (Manual Save)**
- Used for: Application settings, LLM configuration
- Behavior: Changes are accumulated locally and saved when user clicks "Save Changes"
- Implementation:
  - Has "Save Changes" button that becomes enabled when changes are detected
  - Uses local state management with `isDirty` tracking
  - Uses `useSaveSettings` hook to save all changes at once
  - Example: LLM tab, Application tab
- Benefits: Allows bulk changes, explicit save action, can validate all fields before saving

**When to use each pattern:**
- Use Pattern 1 (Immediate Save) for entity management where each item is independent
- Use Pattern 2 (Manual Save) for configuration forms where settings are interdependent or need validation

### Adding New LLM Models

To add a new LLM model to OpenHands, you need to update multiple files across both frontend and backend:

#### Model Configuration Procedure:

1. **Frontend Model Arrays** (`frontend/src/utils/verified-models.ts`):
   - Add the model to `VERIFIED_MODELS` array (main list of all verified models)
   - Add to provider-specific arrays based on the model's provider:
     - `VERIFIED_OPENAI_MODELS` for OpenAI models
     - `VERIFIED_ANTHROPIC_MODELS` for Anthropic models
     - `VERIFIED_MISTRAL_MODELS` for Mistral models
     - `VERIFIED_OPENHANDS_MODELS` for models available through OpenHands provider

2. **Backend CLI Integration** (`openhands/cli/utils.py`):
   - Add the model to the appropriate `VERIFIED_*_MODELS` arrays
   - This ensures the model appears in CLI model selection

3. **Backend Model List** (`openhands/utils/llm.py`):
   - **CRITICAL**: Add the model to the `openhands_models` list (lines 57-66) if using OpenHands provider
   - This is required for the model to appear in the frontend model selector
   - Format: `'openhands/model-name'` (e.g., `'openhands/o3'`)

4. **Backend LLM Configuration** (`openhands/llm/llm.py`):
   - Add to feature-specific arrays based on model capabilities:
     - `FUNCTION_CALLING_SUPPORTED_MODELS` if the model supports function calling
     - `REASONING_EFFORT_SUPPORTED_MODELS` if the model supports reasoning effort parameters
     - `CACHE_PROMPT_SUPPORTED_MODELS` if the model supports prompt caching
     - `MODELS_WITHOUT_STOP_WORDS` if the model doesn't support stop words

5. **Validation**:
   - Run backend linting: `pre-commit run --config ./dev_config/python/.pre-commit-config.yaml`
   - Run frontend linting: `cd frontend && npm run lint:fix`
   - Run frontend build: `cd frontend && npm run build`

#### Model Verification Arrays:

- **VERIFIED_MODELS**: Main array of all verified models shown in the UI
- **VERIFIED_OPENAI_MODELS**: OpenAI models (LiteLLM doesn't return provider prefix)
- **VERIFIED_ANTHROPIC_MODELS**: Anthropic models (LiteLLM doesn't return provider prefix)
- **VERIFIED_MISTRAL_MODELS**: Mistral models (LiteLLM doesn't return provider prefix)
- **VERIFIED_OPENHANDS_MODELS**: Models available through OpenHands managed provider

#### Model Feature Support Arrays:

- **FUNCTION_CALLING_SUPPORTED_MODELS**: Models that support structured function calling
- **REASONING_EFFORT_SUPPORTED_MODELS**: Models that support reasoning effort parameters (like o1, o3)
- **CACHE_PROMPT_SUPPORTED_MODELS**: Models that support prompt caching for efficiency
- **MODELS_WITHOUT_STOP_WORDS**: Models that don't support stop word parameters

#### Frontend Model Integration:

- Models are automatically available in the model selector UI once added to verified arrays
- The `extractModelAndProvider` utility automatically detects provider from model arrays
- Provider-specific models are grouped and prioritized in the UI selection

#### CLI Model Integration:

- Models appear in CLI provider selection based on the verified arrays
- The `organize_models_and_providers` function groups models by provider
- Default model selection prioritizes verified models for each provider

---

## Quick Reference

### Common Commands

```bash
# Setup
make build                          # Build entire project
make install-pre-commit-hooks       # Install pre-commit hooks

# Backend
poetry run pytest tests/unit/       # Run backend tests
poetry run pytest tests/unit/test_xxx.py::test_name  # Run specific test
pre-commit run --config ./dev_config/python/.pre-commit-config.yaml  # Lint backend

# Frontend
cd frontend
npm install                         # Install dependencies
npm run test                        # Run tests
npm run lint:fix                    # Lint and fix
npm run build                       # Build for production

# Enterprise
cd enterprise
poetry install --with dev,test      # Install enterprise dependencies
PYTHONPATH=".:$PYTHONPATH" poetry run pytest tests/unit/  # Run tests
make start-backend                  # Run enterprise server

# VSCode Extension
cd openhands/integrations/vscode
npm install                         # Install dependencies
npm run lint:fix                    # Lint and fix
npm run compile                     # Compile TypeScript
```

### Important File Locations

- **Agent implementations**: `openhands/agenthub/`
- **LLM integration**: `openhands/llm/`
- **Runtime implementations**: `openhands/runtime/`
- **Event definitions**: `openhands/events/`
- **API client**: `frontend/src/api/`
- **React components**: `frontend/src/components/`
- **TanStack Query hooks**: `frontend/src/hooks/query/` and `frontend/src/hooks/mutation/`
- **Backend tests**: `tests/unit/`
- **Frontend tests**: `frontend/__tests__/` and `frontend/tests/`
- **Enterprise code**: `enterprise/`
- **Microagents**: `.openhands/microagents/`

### Getting Help

- **Repository microagents**: Check `.openhands/microagents/` for repo-specific guidance
- **Module documentation**: Look for `AGENTS.md` files in subdirectories
- **Contributing guide**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Development guide**: See [Development.md](Development.md)
- **Glossary**: See [.openhands/microagents/glossary.md](.openhands/microagents/glossary.md)

---

**Happy Coding! 🚀**

For detailed module-specific guidance, navigate to the AGENTS.md files in each directory.
