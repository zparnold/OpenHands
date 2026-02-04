# Persistent Storage Implementation

This directory contains the implementation of PostgreSQL and Redis-backed persistent storage for OpenHands, as specified in DESIRED_FEATURES.md #2.

## Overview

The implementation provides:

1. **PostgreSQL for Relational Data**
   - User identities and profiles
   - Organizations for multi-tenancy
   - Session persistence
   - Encrypted secrets storage

2. **Redis for Distributed Systems**
   - Caching with TTL support
   - Rate limiting
   - Distributed locks
   - Task queues

## Directory Structure

```
openhands/storage/
├── models/                    # SQLAlchemy database models
│   ├── user.py               # User identity model
│   ├── organization.py       # Organization and membership models
│   ├── session.py            # Session persistence model
│   └── secret.py             # Encrypted secrets model
├── settings/
│   └── postgres_settings_store.py  # PostgreSQL settings storage
├── secrets/
│   └── postgres_secrets_store.py   # PostgreSQL secrets storage
└── redis_cache.py            # Redis cache manager

openhands/app_server/app_lifespan/alembic/versions/
└── 006.py                    # Database migration for new tables
```

## Key Features

### Database Models

**User Model** (`user.py`)
- User ID, email, display name
- Created/updated timestamps
- Relationships to sessions, secrets, and organizations

**Organization Model** (`organization.py`)
- Organization ID and name
- Member management with roles (admin/member)
- Relationships to sessions and secrets

**Session Model** (`session.py`)
- Session persistence with JSON state
- Linked to users and organizations
- Conversation ID tracking

**Secret Model** (`secret.py`)
- Encrypted storage using JWE
- User-level and organization-level secrets
- Description field for documentation

### Storage Implementations

**PostgresSettingsStore**
- Stores user settings in PostgreSQL
- Async operations using SQLAlchemy
- User profile management

**PostgresSecretsStore**
- Secure storage with automatic encryption
- Organization and user-level secrets
- CRUD operations for secrets

**RedisCacheManager**
- Key-value caching with TTL
- Rate limiting with sliding window
- Distributed locks for coordination
- Task queue operations

## Usage

### Environment Variables

Required environment variables:

```bash
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=openhands
DB_USER=postgres
DB_PASS=secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=secure_password

# JWT Secret for encryption
JWT_SECRET=your_jwt_secret
```

### Using the Stores

**Settings Store:**

```python
from openhands.storage.settings.postgres_settings_store import PostgresSettingsStore

# Requires AsyncSession from request context
store = PostgresSettingsStore(session, user_id='user123')
settings = await store.load()
await store.store(settings)
```

**Secrets Store:**

```python
from openhands.storage.secrets.postgres_secrets_store import PostgresSecretsStore
from pydantic import SecretStr

store = PostgresSecretsStore(session, user_id='user123', organization_id='org123')
await store.store_secret('api_key', SecretStr('secret_value'), 'API Key')
secret = await store.get_secret('api_key')
await store.delete_secret('api_key')
```

**Redis Cache:**

```python
from openhands.storage.redis_cache import RedisCacheManager

cache = RedisCacheManager(host='localhost', port=6379, password='password')

# Caching
await cache.set('key', {'data': 'value'}, ttl=300)
value = await cache.get('key')

# Rate limiting
allowed, remaining = await cache.rate_limit('user:123', max_requests=100, window_seconds=60)

# Distributed locks
if await cache.acquire_lock('resource:123', ttl=30):
    try:
        # Critical section
        pass
    finally:
        await cache.release_lock('resource:123')

# Task queues
await cache.push_to_queue('tasks', {'task': 'data'})
task = await cache.pop_from_queue('tasks')
```

## Database Migrations

Migrations are managed with Alembic:

```bash
# Run migrations
alembic -c openhands/app_server/app_lifespan/alembic.ini upgrade head

# Check current version
alembic -c openhands/app_server/app_lifespan/alembic.ini current

# Create new migration
alembic -c openhands/app_server/app_lifespan/alembic.ini revision --autogenerate -m "Description"
```

## Testing

Unit tests are provided for:
- Database models (`tests/unit/storage/models/test_models.py`)
- Redis cache manager (`tests/unit/storage/test_redis_cache.py`)

Run tests with:

```bash
poetry run pytest tests/unit/storage/
```

## Security Considerations

1. **Secret Encryption**: All secrets are encrypted using JWE before storage
2. **Connection Security**: Use SSL/TLS for database connections in production
3. **Access Control**: Implement proper authentication and authorization
4. **Password Security**: Use strong passwords for database and Redis
5. **Network Isolation**: Limit database access to authorized hosts only

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- OpenHands connected to both

### Kubernetes/Helm

```bash
helm install openhands ./helm/openhands
```

The Helm chart includes:
- PostgreSQL (Bitnami chart)
- Redis (Bitnami chart)
- OpenHands with proper connections

See `helm/openhands/values.yaml` for configuration options.

## Troubleshooting

**Connection Errors:**
- Verify database host and port are correct
- Check credentials
- Ensure database service is running

**Migration Errors:**
- Check current migration version
- Review migration logs
- Consider manual intervention if needed

**Redis Connection Issues:**
- Verify Redis host and port
- Check authentication password
- Ensure Redis service is running

## Additional Resources

- [Database Setup Guide](../../docs/DATABASE_SETUP.md)
- [File vs PostgreSQL Storage](../../docs/FILE_VS_POSTGRES_STORAGE.md) – Which components use file storage vs database by default
- [DESIRED_FEATURES.md](../../DESIRED_FEATURES.md) - Original feature specification
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
