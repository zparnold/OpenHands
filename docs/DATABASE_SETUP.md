# Database Setup Guide

This guide explains how to set up and configure PostgreSQL and Redis for OpenHands persistent storage.

## Overview

OpenHands now supports persistent storage using PostgreSQL for relational data and Redis for caching, rate limiting, and task queues. This enables:

- **User Management**: Store user identities and profiles
- **Multi-Tenancy**: Support for organizations with role-based access
- **Session Persistence**: Maintain session state across restarts
- **Secrets Management**: Securely store API keys and credentials with encryption
- **Distributed Caching**: Fast access to frequently used data
- **Rate Limiting**: Prevent API abuse with distributed rate limits

## Quick Start with Docker Compose

```bash
# Start all services including PostgreSQL and Redis
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f postgres redis
```

## Environment Variables

Configure database connections using environment variables:

```env
# PostgreSQL Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=openhands
DB_USER=postgres
DB_PASS=your_secure_password

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_password
```

## Kubernetes Deployment

Use the Helm chart with PostgreSQL and Redis dependencies:

```bash
# Add Bitnami repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install OpenHands with databases
helm install openhands ./helm/openhands
```

See the full documentation at `helm/openhands/README.md` for configuration options.

## Database Schema

The system includes these core tables:
- **users**: User identities
- **organizations**: Multi-tenant organizations
- **organization_memberships**: User-organization relationships
- **sessions**: Persistent session state
- **secrets**: Encrypted API keys and credentials

## Migrations

Database migrations are managed with Alembic and run automatically on startup. To run manually:

```bash
alembic -c openhands/app_server/app_lifespan/alembic.ini upgrade head
```

## Additional Resources

- [File vs PostgreSQL Storage](./FILE_VS_POSTGRES_STORAGE.md) – Documents which components use file storage vs database by default
- [Full Database Setup Guide](./database-setup-full.md)
- [Security Best Practices](./security.md)
- [Helm Chart Documentation](../helm/openhands/README.md)
