# Deployment Guide for OpenHands with PostgreSQL and Redis

This guide provides step-by-step instructions for deploying OpenHands with PostgreSQL and Redis backing stores in various environments.

## Table of Contents

- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Development Setup](#development-setup)
- [Production Deployment (Kubernetes)](#production-deployment-kubernetes)
- [Cloud Deployments](#cloud-deployments)
- [Migration from File-Based Storage](#migration-from-file-based-storage)

## Quick Start (Docker Compose)

The fastest way to get started with OpenHands using PostgreSQL and Redis:

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available

### Steps

1. **Clone the repository:**

```bash
git clone https://github.com/OpenHands/OpenHands.git
cd OpenHands
```

2. **Create environment file:**

```bash
cp .env.example .env
```

3. **Configure your environment:**

Edit `.env` and set at least:

```env
# Required: LLM API Key
LLM_API_KEY=your-openai-or-anthropic-api-key

# Optional: Change default passwords (recommended)
DB_PASS=your_secure_postgres_password
REDIS_PASSWORD=your_secure_redis_password
JWT_SECRET=$(openssl rand -base64 32)
```

4. **Start all services:**

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on localhost:5432
- Redis on localhost:6379
- OpenHands on localhost:3000

5. **Verify services are running:**

```bash
docker-compose ps
```

All services should show status "Up".

6. **Access OpenHands:**

Open http://localhost:3000 in your browser.

### Troubleshooting

**Services won't start:**
```bash
# Check logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs openhands

# Ensure ports are not in use
netstat -an | grep -E '5432|6379|3000'
```

**Database connection errors:**
```bash
# Check PostgreSQL is accessible
docker-compose exec postgres psql -U postgres -d openhands -c '\dt'

# Check Redis is accessible
docker-compose exec redis redis-cli -a redis PING
```

## Development Setup

For local development with hot-reload and debugging:

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker for PostgreSQL and Redis

### Steps

1. **Start only database services:**

```bash
docker-compose up -d postgres redis
```

2. **Install dependencies:**

```bash
# Backend
poetry install

# Frontend
cd frontend && npm install && cd ..
```

3. **Set environment variables:**

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=openhands
export DB_USER=postgres
export DB_PASS=postgres
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=redis
export LLM_API_KEY=your-api-key
```

4. **Run database migrations:**

```bash
alembic -c openhands/app_server/app_lifespan/alembic.ini upgrade head
```

5. **Start the development server:**

```bash
# Backend
poetry run python -m openhands.server.listen

# Frontend (in separate terminal)
cd frontend && npm run dev
```

## Production Deployment (Kubernetes)

For production deployments, use Kubernetes with Helm:

### Prerequisites

- Kubernetes cluster 1.24+
- Helm 3.8+
- kubectl configured
- Persistent storage provisioner

### Basic Deployment

1. **Add Bitnami repository:**

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

2. **Create namespace:**

```bash
kubectl create namespace openhands
```

3. **Create secrets:**

```bash
# LLM API Key
kubectl create secret generic openhands-secrets \
  --from-literal=llm-api-key=your-api-key \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  -n openhands

# Database password (if using external database)
kubectl create secret generic openhands-db \
  --from-literal=password=your-db-password \
  -n openhands
```

4. **Create custom values file:**

See `helm/openhands/examples/database-values.yaml` for a complete example.

Minimal `values.yaml`:

```yaml
replicaCount: 2

config:
  llm:
    apiKey: "your-llm-api-key"

postgresql:
  enabled: true
  auth:
    password: "secure-postgres-password"
  primary:
    persistence:
      size: 50Gi

redis:
  enabled: true
  auth:
    password: "secure-redis-password"
  master:
    persistence:
      size: 10Gi

ingress:
  enabled: true
  hosts:
    - host: openhands.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
```

5. **Install the chart:**

```bash
helm install openhands ./helm/openhands \
  -f values.yaml \
  -n openhands
```

6. **Wait for deployment:**

```bash
kubectl get pods -n openhands -w
```

7. **Access the application:**

```bash
# If using LoadBalancer
kubectl get svc -n openhands

# If using Ingress
kubectl get ingress -n openhands
```

### High Availability Setup

For HA deployments:

```yaml
replicaCount: 3

postgresql:
  enabled: true
  architecture: replication
  replication:
    numSynchronousReplicas: 1
  primary:
    persistence:
      size: 100Gi
  readReplicas:
    replicaCount: 2
    persistence:
      size: 100Gi

redis:
  enabled: true
  architecture: replication
  master:
    persistence:
      size: 20Gi
  replica:
    replicaCount: 2
    persistence:
      size: 20Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

## Cloud Deployments

### AWS (EKS + RDS + ElastiCache)

1. **Create RDS PostgreSQL instance:**

```bash
aws rds create-db-instance \
  --db-instance-identifier openhands-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16.1 \
  --master-username postgres \
  --master-user-password your-password \
  --allocated-storage 100
```

2. **Create ElastiCache Redis cluster:**

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id openhands-cache \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --num-cache-nodes 1
```

3. **Use external database configuration:**

```yaml
postgresql:
  enabled: false

redis:
  enabled: false

externalDatabase:
  enabled: true
  host: openhands-db.xxx.region.rds.amazonaws.com
  port: 5432
  database: openhands
  username: postgres
  password: your-password

externalRedis:
  enabled: true
  host: openhands-cache.xxx.cache.amazonaws.com
  port: 6379
```

### GCP (GKE + Cloud SQL + Memorystore)

1. **Create Cloud SQL instance:**

```bash
gcloud sql instances create openhands-db \
  --database-version=POSTGRES_16 \
  --tier=db-custom-2-8192 \
  --region=us-central1
```

2. **Create Memorystore Redis instance:**

```bash
gcloud redis instances create openhands-cache \
  --size=5 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

3. **Configure with Cloud SQL Proxy:**

```yaml
externalDatabase:
  enabled: true
  host: localhost  # via Cloud SQL proxy
  port: 5432

envVars:
  - name: GCP_DB_INSTANCE
    value: "project:region:instance"
  - name: GCP_PROJECT
    value: "your-project"
  - name: GCP_REGION
    value: "us-central1"
```

### Azure (AKS + Azure Database + Azure Cache)

1. **Create Azure Database for PostgreSQL:**

```bash
az postgres flexible-server create \
  --name openhands-db \
  --resource-group openhands-rg \
  --location eastus \
  --version 16 \
  --tier Burstable \
  --sku-name Standard_B2s
```

2. **Create Azure Cache for Redis:**

```bash
az redis create \
  --name openhands-cache \
  --resource-group openhands-rg \
  --location eastus \
  --sku Basic \
  --vm-size c1
```

3. **Configure external connections:**

```yaml
externalDatabase:
  enabled: true
  host: openhands-db.postgres.database.azure.com
  port: 5432

externalRedis:
  enabled: true
  host: openhands-cache.redis.cache.windows.net
  port: 6380  # SSL port
```

## Migration from File-Based Storage

If you're migrating from file-based storage:

### 1. Backup Current Data

```bash
# Backup workspace and settings
tar czf openhands-backup-$(date +%Y%m%d).tar.gz ~/.openhands
```

### 2. Set Up Database

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run migrations
alembic -c openhands/app_server/app_lifespan/alembic.ini upgrade head
```

### 3. Migrate Data

Currently, data migration needs to be done manually:

1. **Export settings from files**
2. **Import into database using API or direct SQL**
3. **Verify data integrity**
4. **Switch to database-backed stores**

### 4. Update Configuration

Update your configuration to use PostgreSQL stores:

```python
# In server configuration
settings_store_class = "openhands.storage.settings.postgres_settings_store.PostgresSettingsStore"
secrets_store_class = "openhands.storage.secrets.postgres_secrets_store.PostgresSecretsStore"
```

### 5. Test and Verify

1. **Start OpenHands with new configuration**
2. **Verify user sessions work**
3. **Check secrets are accessible**
4. **Test conversation persistence**

### 6. Cleanup

Once confirmed working:

```bash
# Keep backup for safety
mv ~/.openhands ~/.openhands.backup
```

## Monitoring and Maintenance

### Health Checks

```bash
# PostgreSQL
kubectl exec -it deployment/openhands-postgresql -n openhands -- \
  psql -U postgres -d openhands -c "SELECT version();"

# Redis
kubectl exec -it deployment/openhands-redis-master -n openhands -- \
  redis-cli PING
```

### Backups

```bash
# PostgreSQL backup
kubectl exec -it deployment/openhands-postgresql -n openhands -- \
  pg_dump -U postgres openhands > backup.sql

# Redis backup
kubectl exec -it deployment/openhands-redis-master -n openhands -- \
  redis-cli SAVE
```

### Scaling

```bash
# Scale OpenHands replicas
kubectl scale deployment/openhands --replicas=5 -n openhands

# For database scaling, see cloud provider documentation
```

## Security Best Practices

1. **Use Strong Passwords**: Generate secure passwords for all services
2. **Enable TLS**: Use SSL/TLS for all database connections
3. **Network Policies**: Implement Kubernetes network policies
4. **Secrets Management**: Use proper secret management (Vault, Sealed Secrets)
5. **Regular Updates**: Keep all components updated
6. **Backup Strategy**: Implement regular automated backups
7. **Access Control**: Use RBAC for Kubernetes access

## Support and Resources

- [Database Setup Guide](./DATABASE_SETUP.md)
- [Helm Chart Documentation](../helm/openhands/README.md)
- [GitHub Issues](https://github.com/OpenHands/OpenHands/issues)
- [Community Discord](https://discord.gg/openhands)
