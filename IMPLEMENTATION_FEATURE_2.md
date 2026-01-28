# Implementation Summary: Feature #2 - Persistent Storage & Relational Database

## Overview

This implementation adds PostgreSQL and Redis support to OpenHands, enabling persistent storage for users, organizations, sessions, and secrets as specified in DESIRED_FEATURES.md #2.

## What Was Implemented

### 1. Database Models (SQLAlchemy)

Created comprehensive database models for:

- **User** (`openhands/storage/models/user.py`)
  - User identity with email and display name
  - Relationships to sessions, secrets, and organizations
  
- **Organization** (`openhands/storage/models/organization.py`)
  - Multi-tenant organization support
  - Organization memberships with roles (admin/member)
  
- **Session** (`openhands/storage/models/session.py`)
  - Persistent session state storage
  - Links to users and organizations
  - JSON state field for flexibility
  
- **Secret** (`openhands/storage/models/secret.py`)
  - Encrypted storage for API keys and credentials
  - Organization-level and user-level secrets
  - Automatic JWE encryption

### 2. Storage Implementations

- **PostgresSettingsStore** (`openhands/storage/settings/postgres_settings_store.py`)
  - Async PostgreSQL-backed settings storage
  - User profile management
  
- **PostgresSecretsStore** (`openhands/storage/secrets/postgres_secrets_store.py`)
  - Secure secret storage with automatic encryption
  - CRUD operations for user and organization secrets
  
- **RedisCacheManager** (`openhands/storage/redis_cache.py`)
  - Key-value caching with TTL
  - Rate limiting with sliding window
  - Distributed locks
  - Task queue operations

### 3. Database Migration

- **Migration 006** (`openhands/app_server/app_lifespan/alembic/versions/006.py`)
  - Creates all new tables (users, organizations, organization_memberships, sessions, secrets)
  - Proper indexes for query performance
  - Foreign key relationships

### 4. Deployment Infrastructure

#### Docker Compose

Updated `docker-compose.yml` with:
- PostgreSQL 16 service with health checks
- Redis 7 service with authentication
- Persistent volumes for data
- Environment variable configuration
- Proper service dependencies

#### Kubernetes/Helm

Updated Helm chart with:
- Bitnami PostgreSQL and Redis chart dependencies
- Configuration for internal or external databases
- Environment variable injection
- Support for HA deployments
- Example values file for easy deployment

#### Scripts

- `scripts/init-db.sh` - Database initialization and migration script

### 5. Configuration

- `.env.example` - Template for environment variables
- Database connection settings
- Redis configuration
- JWT secret for encryption

### 6. Testing

Created unit tests for:
- Database models (`tests/unit/storage/models/test_models.py`)
- Redis cache operations (`tests/unit/storage/test_redis_cache.py`)

### 7. Documentation

Comprehensive documentation including:

- **DATABASE_SETUP.md** - Quick start guide for database setup
- **DEPLOYMENT_GUIDE.md** - Complete deployment guide for all environments
  - Docker Compose
  - Kubernetes/Helm
  - AWS (RDS + ElastiCache)
  - GCP (Cloud SQL + Memorystore)
  - Azure (Database + Cache)
- **README_PERSISTENT_STORAGE.md** - Implementation details and API usage
- Example Kubernetes values file with database configuration

## Architecture

### Database Schema

```
users
├── id (PK)
├── email (unique)
├── display_name
├── created_at
└── updated_at

organizations
├── id (PK)
├── name
├── created_at
└── updated_at

organization_memberships
├── id (PK)
├── user_id (FK -> users)
├── organization_id (FK -> organizations)
├── role
└── created_at

sessions
├── id (PK)
├── user_id (FK -> users)
├── organization_id (FK -> organizations)
├── conversation_id
├── state (JSON)
├── created_at
├── updated_at
└── last_accessed_at

secrets
├── id (PK)
├── user_id (FK -> users)
├── organization_id (FK -> organizations)
├── key
├── value (encrypted)
├── description
├── created_at
└── updated_at
```

### Redis Usage

- **Caching**: `cache:{key}` - Temporary data storage
- **Rate Limiting**: `ratelimit:{resource}` - Request counting
- **Locks**: `lock:{resource}` - Distributed coordination
- **Queues**: `queue:{name}` - Background task processing

## Security Features

1. **Secret Encryption**: All secrets encrypted with JWE before database storage
2. **Password Security**: Secure password handling for database connections
3. **Connection Security**: Support for SSL/TLS connections
4. **Access Control**: Organization-based secret scoping
5. **JWT Integration**: Uses existing JWT secret for encryption key

## Deployment Options

### Development (Docker Compose)

```bash
docker-compose up -d
```

### Production (Kubernetes)

```bash
helm install openhands ./helm/openhands \
  -f helm/openhands/examples/database-values.yaml
```

### External Databases

Support for managed database services:
- AWS RDS + ElastiCache
- GCP Cloud SQL + Memorystore
- Azure Database + Azure Cache for Redis

## Environment Variables

Key environment variables:

```bash
# PostgreSQL
DB_HOST=postgres
DB_PORT=5432
DB_NAME=openhands
DB_USER=postgres
DB_PASS=secure_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_password

# Security
JWT_SECRET=your_jwt_secret
```

## Testing

Run tests with:

```bash
# Unit tests
poetry run pytest tests/unit/storage/

# Specific test files
poetry run pytest tests/unit/storage/models/test_models.py
poetry run pytest tests/unit/storage/test_redis_cache.py
```

## Future Enhancements

Recommended future work:

1. **Configuration Integration**: Wire up stores in application config
2. **Data Migration**: Automated migration from file-based storage
3. **Integration Tests**: Tests with running database instances
4. **Monitoring**: Add Prometheus metrics
5. **Backup Automation**: Scheduled backup scripts
6. **Performance Tuning**: Query optimization and connection pooling
7. **Admin UI**: Web interface for user/organization management

## Compatibility

- PostgreSQL 12+
- Redis 6+
- Python 3.12+
- Kubernetes 1.24+
- Docker 20.10+

## Breaking Changes

None - this is a new feature that doesn't affect existing functionality. The implementation is additive and maintains backward compatibility with file-based storage.

## Migration Path

For existing installations:

1. Deploy PostgreSQL and Redis
2. Run database migrations
3. Keep file-based storage as fallback
4. Gradually migrate to database storage
5. Update configuration to use new stores

## Resources

- [Database Setup Guide](./DATABASE_SETUP.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Storage Implementation Details](../openhands/storage/README_PERSISTENT_STORAGE.md)
- [Kubernetes Example](../helm/openhands/examples/database-values.yaml)

## Support

For issues or questions:
- GitHub Issues: https://github.com/OpenHands/OpenHands/issues
- Documentation: See docs/ directory

## License

Same as OpenHands main license (MIT)

---

**Implementation Date**: January 28, 2026  
**Feature Reference**: DESIRED_FEATURES.md #2  
**Status**: Complete - Ready for integration and testing
