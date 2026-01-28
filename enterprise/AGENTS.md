# Enterprise Development Guide (enterprise/)

This guide provides detailed information for developing OpenHands Enterprise features.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Development Setup](#development-setup)
4. [Key Modules](#key-modules)
5. [Testing Guidelines](#testing-guidelines)
6. [Database Migrations](#database-migrations)
7. [Common Tasks](#common-tasks)

---

## Overview

The `enterprise/` directory contains additional functionality that extends the open-source OpenHands codebase. Enterprise features are source-available under the Polyform Free Trial License (30-day limit).

**Key features:**
- Authentication and user management (Keycloak integration)
- Database migrations (Alembic)
- Integration services (GitHub, GitLab, Jira, Linear, Slack)
- Billing and subscription management (Stripe)
- Telemetry and analytics (PostHog, custom metrics framework)
- Multi-user support with RBAC
- Conversation sharing and collaboration

---

## Architecture

**Enterprise extends OpenHands core:**
```
┌─────────────────────────────────────┐
│   Enterprise Server (server/)       │ ← Extensions to core server
├─────────────────────────────────────┤
│   Integrations (integrations/)      │ ← External service integrations
├─────────────────────────────────────┤
│   Storage (storage/)                │ ← Enterprise data models
├─────────────────────────────────────┤
│   Sync (sync/)                      │ ← Background sync tasks
├─────────────────────────────────────┤
│   Core OpenHands (../openhands/)    │ ← Open-source foundation
└─────────────────────────────────────┘
```

**Key concepts:**
- **Dynamic imports**: Enterprise server extends core via dynamic imports
- **Shared storage**: Uses same database infrastructure as core
- **Alembic migrations**: Database schema changes tracked in `migrations/`
- **Service pattern**: Each integration follows service/storage/routes pattern

---

## Development Setup

### Prerequisites

- Python 3.12
- Poetry (for dependency management)
- Node.js 22.x (for frontend)
- Docker (optional, for PostgreSQL)

### Setup Steps

1. **Build main OpenHands project:**
```bash
make build
```

2. **Install enterprise dependencies:**
```bash
cd enterprise
poetry install --with dev,test
```
⚠️ **Note**: This can take a very long time. Be patient.

3. **Set up pre-commit hooks:**
```bash
poetry run pre-commit install --config ./dev_config/python/.pre-commit-config.yaml
```

### Running Enterprise

**Development mode (backend only):**
```bash
cd enterprise
make start-backend
```

**Full application (backend + frontend):**
```bash
cd enterprise
make run
```

**Running tests:**
```bash
# Full enterprise test suite
PYTHONPATH=".:$PYTHONPATH" poetry run --project=enterprise pytest --forked -n auto -s ./enterprise/tests/unit --cov=enterprise --cov-branch

# Test specific module
cd enterprise
PYTHONPATH=".:$PYTHONPATH" poetry run pytest tests/unit/telemetry/ --confcutdir=tests/unit/telemetry

# Linting (IMPORTANT: use --show-diff-on-failure to match GitHub CI)
poetry run pre-commit run --all-files --show-diff-on-failure --config ./dev_config/python/.pre-commit-config.yaml
```

---

## Key Modules

### server/
Enterprise server extensions.

**Main files:**
- `saas_server.py`: Enterprise FastAPI application
- `routes/`: Additional API endpoints
- `middleware/`: Authentication and authorization
- `conversation_callback_processor/`: Background task processor
- `maintenance_task_processor/`: Maintenance tasks
- `sharing/`: Conversation sharing features

See [server/AGENTS.md](server/AGENTS.md) for server development.

### integrations/
External service integrations.

**Services:**
- **GitHub**: Repository integration, PR management, webhooks
- **GitLab**: Similar to GitHub for GitLab instances
- **Jira**: Issue tracking integration
- **Linear**: Modern issue tracking
- **Slack**: Team communication and notifications

**Pattern for each integration:**
```
integrations/[service]/
├── service.py          # Business logic
├── storage.py          # Data models and persistence
├── routes.py           # API endpoints
└── webhooks.py         # Webhook handlers (if applicable)
```

See [integrations/AGENTS.md](integrations/AGENTS.md) for integration development.

### storage/
Enterprise database models.

**Main files:**
- `data_models/`: SQLAlchemy models
  - `user.py`: User model
  - `organization.py`: Organization model
  - `subscription.py`: Billing and subscription
  - `integration.py`: Integration configurations
- `database.py`: Database session management
- `repositories/`: Data access layer

**Database:**
- PostgreSQL in production
- SQLite in-memory for unit tests

### migrations/
Alembic database migrations.

**Structure:**
```
migrations/
├── versions/           # Migration files
├── env.py             # Alembic environment
└── script.py.mako     # Migration template
```

See [Database Migrations](#database-migrations) section below.

### sync/
Background synchronization tasks.

**Examples:**
- Syncing GitHub repositories
- Updating issue status
- Processing webhooks

### experiments/
Experimental features and A/B tests.

### telemetry/
Analytics and metrics.

**Features:**
- PostHog integration
- Custom metrics framework
- Event tracking
- Performance monitoring

---

## Testing Guidelines

### Test Structure

Enterprise tests follow the same structure as core tests but are in `enterprise/tests/`:

```
enterprise/tests/
├── unit/              # Unit tests
│   ├── integrations/  # Integration tests
│   ├── storage/       # Storage tests
│   ├── server/        # Server tests
│   └── ...
└── conftest.py        # Shared fixtures
```

### Best Practices

**Database Testing:**
- Use SQLite in-memory databases (`sqlite:///:memory:`) for unit tests
- Never use real PostgreSQL in unit tests
- Create module-specific `conftest.py` files with database fixtures
- Mock external database connections

**Import Patterns:**
- Use relative imports without `enterprise.` prefix
- Example: `from storage.database import session_maker` not `from enterprise.storage.database import session_maker`
- This ensures code works in both OpenHands and enterprise contexts

**Test Structure:**
- Place tests in `enterprise/tests/unit/` following source structure
- Use `--confcutdir=tests/unit/[module]` when testing specific modules
- Create comprehensive fixtures for complex objects
- Write platform-agnostic tests (no hardcoded OS-specific assertions)

**Mocking Strategy:**
- Use `AsyncMock` for async operations
- Use `MagicMock` for complex objects
- Mock all external dependencies (databases, APIs, file systems)
- Use `patch` with correct import paths (relative, not absolute with `enterprise.`)
- Test both success and failure scenarios

**Coverage Goals:**
- Aim for 90%+ test coverage on new enterprise modules
- Focus on critical business logic and error handling paths
- Use `--cov-report=term-missing` to identify uncovered lines

### Example Test

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from storage.database import get_session
from integrations.github.service import GitHubService

@pytest.fixture
async def db_session():
    """Create in-memory SQLite database for testing."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from storage.data_models.base import Base
    
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
async def test_github_integration(db_session):
    """Test GitHub integration service."""
    with patch('integrations.github.service.GitHubAPI') as mock_github:
        mock_github.return_value.get_repo = AsyncMock(return_value={
            'name': 'test-repo',
            'full_name': 'user/test-repo'
        })
        
        service = GitHubService(db_session)
        repo = await service.get_repository('user/test-repo')
        
        assert repo['name'] == 'test-repo'
```

---

## Database Migrations

Enterprise uses **Alembic** for database migrations.

### Creating a Migration

1. **Make schema changes** in `enterprise/storage/data_models/`

2. **Generate migration:**
```bash
cd enterprise
alembic revision --autogenerate -m "Add new table"
```

3. **Review migration file** in `migrations/versions/`

4. **Test migration:**
```bash
# Upgrade
alembic upgrade head

# Downgrade
alembic downgrade -1
```

5. **Commit migration file**

### Migration Best Practices

- **Always review auto-generated migrations** - Alembic doesn't catch everything
- **Test both upgrade and downgrade** paths
- **Handle data migrations** carefully
- **Check for conflicts** - CI will detect migration conflicts
- **Use transactions** - Migrations should be atomic
- **Document complex migrations** - Add comments explaining non-obvious changes

### Common Migration Operations

**Add table:**
```python
def upgrade():
    op.create_table(
        'my_table',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
    )

def downgrade():
    op.drop_table('my_table')
```

**Add column:**
```python
def upgrade():
    op.add_column('my_table', sa.Column('new_column', sa.String(255)))

def downgrade():
    op.drop_column('my_table', 'new_column')
```

**Modify column:**
```python
def upgrade():
    op.alter_column('my_table', 'my_column', 
                    type_=sa.String(512))

def downgrade():
    op.alter_column('my_table', 'my_column', 
                    type_=sa.String(255))
```

---

## Common Tasks

### Adding a New Integration

1. **Create integration directory:**
```
enterprise/integrations/myservice/
├── __init__.py
├── service.py      # Business logic
├── storage.py      # Data models
├── routes.py       # API endpoints
└── webhooks.py     # Webhook handlers (if needed)
```

2. **Implement service class:**
```python
# service.py
class MyServiceIntegration:
    def __init__(self, db_session):
        self.db = db_session
    
    async def connect(self, credentials):
        # Implementation
        pass
```

3. **Add data models:**
```python
# storage.py
from sqlalchemy import Column, String, Integer
from storage.data_models.base import Base

class MyServiceConfig(Base):
    __tablename__ = 'myservice_config'
    
    id = Column(Integer, primary_key=True)
    api_key = Column(String, nullable=False)
```

4. **Create migration:**
```bash
alembic revision --autogenerate -m "Add MyService integration"
```

5. **Add routes:**
```python
# routes.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/integrations/myservice")

@router.post("/connect")
async def connect(credentials: dict):
    # Implementation
    pass
```

6. **Register routes** in `enterprise/saas_server.py`

7. **Add tests** in `enterprise/tests/unit/integrations/myservice/`

### Adding Enterprise Settings

1. **Add to data model** in `enterprise/storage/data_models/settings.py`

2. **Create migration** if schema changes

3. **Add API endpoint** in `enterprise/server/routes/settings.py`

4. **Update frontend** (see frontend AGENTS.md)

5. **Add tests**

### Adding Telemetry Event

1. **Define event** in `enterprise/telemetry/events.py`:
```python
class MyEvent(TelemetryEvent):
    event_name = "my_event"
    properties: Dict[str, Any]
```

2. **Track event** in code:
```python
from telemetry.tracker import track_event

track_event(MyEvent(properties={
    'user_id': user_id,
    'action': 'completed',
}))
```

3. **Add tests** to verify event tracking

---

## Integration Patterns

### Service Layer Pattern

Each integration follows this pattern:

```python
class ServiceIntegration:
    """Service integration business logic."""
    
    def __init__(self, db_session, config):
        self.db = db_session
        self.config = config
    
    async def connect(self, credentials):
        """Connect to external service."""
        pass
    
    async def sync(self):
        """Sync data from external service."""
        pass
    
    async def webhook_handler(self, payload):
        """Handle webhook from external service."""
        pass
```

### Storage Pattern

Each integration has storage models:

```python
class ServiceConfig(Base):
    """Configuration for service integration."""
    __tablename__ = 'service_config'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    api_key = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)

class ServiceData(Base):
    """Data synced from service."""
    __tablename__ = 'service_data'
    
    id = Column(Integer, primary_key=True)
    config_id = Column(Integer, ForeignKey('service_config.id'))
    external_id = Column(String, nullable=False)
    data = Column(JSON)
```

### Routes Pattern

Each integration exposes API endpoints:

```python
from fastapi import APIRouter, Depends, HTTPException
from storage.database import get_session

router = APIRouter(prefix="/api/integrations/service")

@router.post("/connect")
async def connect(
    credentials: dict,
    session = Depends(get_session)
):
    """Connect to external service."""
    # Implementation
    pass

@router.get("/status")
async def get_status(session = Depends(get_session)):
    """Get integration status."""
    # Implementation
    pass

@router.post("/webhook")
async def webhook_handler(
    payload: dict,
    session = Depends(get_session)
):
    """Handle webhook from external service."""
    # Implementation
    pass
```

---

## Best Practices

1. **Use relative imports** - No `enterprise.` prefix
2. **Mock everything in tests** - Use in-memory SQLite for databases
3. **Test both success and failure** - Cover error cases
4. **Document migrations** - Explain complex schema changes
5. **Follow service pattern** - Consistent integration structure
6. **Secure credentials** - Never hardcode API keys
7. **Rate limit external calls** - Respect service limits
8. **Handle webhooks async** - Don't block webhook endpoints
9. **Log extensively** - Use structured logging
10. **Monitor telemetry** - Track important events

---

## Troubleshooting

### Tests failing
- Ensure dependencies installed: `poetry install --with dev,test`
- Check for import errors (use relative imports)
- Verify `PYTHONPATH=".:$PYTHONPATH"` is set
- Check mock paths (relative not absolute)

### Migration conflicts
- Run `alembic heads` to see multiple heads
- Merge migrations or create merge migration
- Test upgrade/downgrade paths

### Database issues
- Check migration status: `alembic current`
- Run migrations: `alembic upgrade head`
- Check logs for SQL errors

### Integration failures
- Verify credentials are correct
- Check rate limits on external service
- Review webhook payload format
- Check for network connectivity

### Linting errors
- **CRITICAL**: Use `--show-diff-on-failure` flag to match CI
- Run: `poetry run pre-commit run --all-files --show-diff-on-failure --config ./dev_config/python/.pre-commit-config.yaml`
- Check import order and formatting
- Verify type hints are correct

---

## Configuration Files

- `enterprise/pyproject.toml` - Python dependencies
- `enterprise/Makefile` - Build and run commands
- `enterprise/alembic.ini` - Alembic configuration
- `enterprise/dev_config/python/` - Linting and type checking
- `enterprise/migrations/` - Database migration files

---

## Important Notes

- **License**: Enterprise code is under Polyform Free Trial License (30-day limit)
- **Dynamic loading**: Enterprise server extends core via dynamic imports
- **Database migrations**: Always test both upgrade and downgrade
- **Testing**: Use SQLite in-memory for unit tests, PostgreSQL for integration tests
- **Import patterns**: Use relative imports without `enterprise.` prefix
- **CI matching**: Always use `--show-diff-on-failure` flag for linting

---

For core OpenHands development, see [../openhands/AGENTS.md](../openhands/AGENTS.md).
For frontend development, see [../frontend/AGENTS.md](../frontend/AGENTS.md).
For general guidelines, see [../AGENTS.md](../AGENTS.md).
