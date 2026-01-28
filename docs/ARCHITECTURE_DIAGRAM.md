# Architecture Diagram: OpenHands Persistent Storage

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          OpenHands Application                       │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   Web Server     │  │   Agent Core     │  │   Sandbox        │ │
│  │   (FastAPI)      │  │                  │  │   Manager        │ │
│  └────────┬─────────┘  └──────────────────┘  └──────────────────┘ │
│           │                                                          │
│           │ Uses Storage Layers                                     │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Storage Layer                              │  │
│  │                                                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │  │
│  │  │SettingsStore    │  │ SecretsStore    │  │SessionStore  │ │  │
│  │  │(PostgreSQL)     │  │(PostgreSQL)     │  │(PostgreSQL)  │ │  │
│  │  └─────────────────┘  └─────────────────┘  └──────────────┘ │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │          Redis Cache Manager                             │ │  │
│  │  │  - Caching    - Rate Limiting    - Locks    - Queues    │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────┬────────────────────────────┘
                       │                  │
                       │                  │
                       ▼                  ▼
         ┌──────────────────────┐  ┌──────────────────────┐
         │    PostgreSQL        │  │       Redis          │
         │                      │  │                      │
         │  ┌────────────────┐ │  │  ┌────────────────┐ │
         │  │ users          │ │  │  │ cache:*        │ │
         │  │ organizations  │ │  │  │ ratelimit:*    │ │
         │  │ org_memberships│ │  │  │ lock:*         │ │
         │  │ sessions       │ │  │  │ queue:*        │ │
         │  │ secrets        │ │  │  └────────────────┘ │
         │  └────────────────┘ │  └──────────────────────┘
         └──────────────────────┘
```

## Data Flow

### User Authentication & Settings

```
User Login
    │
    ▼
┌──────────────────┐
│ Web Request      │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│ PostgresSettingsStore        │
│ - Load user settings         │
│ - Check organization         │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ PostgreSQL Query             │
│ SELECT * FROM users          │
│ WHERE id = ?                 │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Return Settings              │
│ - User profile               │
│ - Organization memberships   │
│ - Preferences                │
└──────────────────────────────┘
```

### Secret Management

```
Store Secret Request
    │
    ▼
┌──────────────────────────────┐
│ PostgresSecretsStore         │
│ - Validate user/org access   │
│ - Encrypt secret with JWE    │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ PostgreSQL Insert            │
│ INSERT INTO secrets          │
│ (key, value_encrypted, ...)  │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Redis Cache Invalidation     │
│ DEL secret:{key}             │
└──────────────────────────────┘
```

### Session Persistence

```
Session Update
    │
    ▼
┌──────────────────────────────┐
│ Session Model                │
│ - Update state (JSON)        │
│ - Update last_accessed_at    │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ PostgreSQL Update            │
│ UPDATE sessions              │
│ SET state = ?, updated_at = ?│
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Redis Session Cache          │
│ SET session:{id} TTL 3600    │
└──────────────────────────────┘
```

### Rate Limiting Flow

```
API Request
    │
    ▼
┌──────────────────────────────┐
│ RedisCacheManager            │
│ rate_limit(user:123)         │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Redis Counter Check          │
│ GET ratelimit:user:123       │
└────────┬─────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌────────────┐
│Count │  │ No counter │
│< Max │  │ exists     │
└───┬──┘  └─────┬──────┘
    │           │
    │           ▼
    │     ┌───────────────┐
    │     │ SETEX counter │
    │     │ TTL 60        │
    │     └───────┬───────┘
    │             │
    ▼             ▼
┌────────────────────┐
│ INCR counter       │
└─────────┬──────────┘
          │
          ▼
┌──────────────────┐
│ Return allowed   │
│ + remaining      │
└──────────────────┘
```

## Database Schema Details

```
users
┌────────────────┬──────────┬─────────────┐
│ Column         │ Type     │ Constraints │
├────────────────┼──────────┼─────────────┤
│ id             │ String   │ PK          │
│ email          │ String   │ Unique, IX  │
│ display_name   │ String   │ Nullable    │
│ created_at     │ DateTime │ UTC         │
│ updated_at     │ DateTime │ UTC         │
└────────────────┴──────────┴─────────────┘
         │
         │ 1:N
         ▼
organization_memberships
┌────────────────┬──────────┬─────────────┐
│ id             │ String   │ PK          │
│ user_id        │ String   │ FK, IX      │
│ organization_id│ String   │ FK, IX      │
│ role           │ String   │ admin/member│
│ created_at     │ DateTime │ UTC         │
└────────────────┴──────────┴─────────────┘
         │
         │ N:1
         ▼
organizations
┌────────────────┬──────────┬─────────────┐
│ id             │ String   │ PK          │
│ name           │ String   │             │
│ created_at     │ DateTime │ UTC         │
│ updated_at     │ DateTime │ UTC         │
└────────────────┴──────────┴─────────────┘
```

## Redis Key Patterns

```
┌─────────────────────────────────────────────────────────┐
│                    Redis Key Space                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  cache:{resource}:{id}                                  │
│  └─ Generic cache with TTL                              │
│     Example: cache:user:123                             │
│                                                          │
│  ratelimit:{resource}:{id}                              │
│  └─ Rate limit counters with sliding window             │
│     Example: ratelimit:api:user:123                     │
│                                                          │
│  lock:{resource}:{id}                                   │
│  └─ Distributed locks with TTL                          │
│     Example: lock:conversation:456                      │
│                                                          │
│  queue:{name}                                           │
│  └─ Task queues (lists)                                 │
│     Example: queue:background_tasks                     │
│                                                          │
│  session:{id}                                           │
│  └─ Session cache for fast access                       │
│     Example: session:abc123def                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Deployment Topology

### Docker Compose (Development)

```
┌─────────────────────────────────────────┐
│         Docker Network (bridge)         │
│                                         │
│  ┌────────────┐  ┌───────────────────┐ │
│  │ PostgreSQL │  │ Redis             │ │
│  │ Port: 5432 │  │ Port: 6379        │ │
│  │ Volume:    │  │ Volume:           │ │
│  │ postgres_  │  │ redis_data        │ │
│  │ data       │  │                   │ │
│  └─────▲──────┘  └────▲──────────────┘ │
│        │              │                 │
│        └──────┬───────┘                 │
│               │                         │
│        ┌──────▼──────┐                  │
│        │ OpenHands   │                  │
│        │ Port: 3000  │                  │
│        │ Volume:     │                  │
│        │ workspace   │                  │
│        │ filestore   │                  │
│        └─────────────┘                  │
└─────────────────────────────────────────┘
```

### Kubernetes (Production)

```
┌──────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                     │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              OpenHands Namespace                     │ │
│  │                                                      │ │
│  │  ┌──────────────────┐  ┌──────────────────┐        │ │
│  │  │ PostgreSQL       │  │ Redis            │        │ │
│  │  │ (StatefulSet)    │  │ (StatefulSet)    │        │ │
│  │  │   - Master       │  │   - Master       │        │ │
│  │  │   - Replicas (2) │  │   - Replicas (2) │        │ │
│  │  │                  │  │                  │        │ │
│  │  │ PVC: 50Gi        │  │ PVC: 10Gi        │        │ │
│  │  └────────▲─────────┘  └────────▲─────────┘        │ │
│  │           │                     │                   │ │
│  │           └──────────┬──────────┘                   │ │
│  │                      │                              │ │
│  │           ┌──────────▼──────────┐                   │ │
│  │           │ OpenHands           │                   │ │
│  │           │ (Deployment)        │                   │ │
│  │           │   - Replicas: 3     │                   │ │
│  │           │   - HPA enabled     │                   │ │
│  │           └──────────┬──────────┘                   │ │
│  │                      │                              │ │
│  │           ┌──────────▼──────────┐                   │ │
│  │           │ Service             │                   │ │
│  │           │ (LoadBalancer)      │                   │ │
│  │           └──────────┬──────────┘                   │ │
│  └──────────────────────┼──────────────────────────────┘ │
│                         │                                │
│              ┌──────────▼──────────┐                     │
│              │ Ingress Controller  │                     │
│              │ (nginx)             │                     │
│              └──────────┬──────────┘                     │
└─────────────────────────┼────────────────────────────────┘
                          │
                ┌─────────▼─────────┐
                │ External Traffic  │
                │ (HTTPS)           │
                └───────────────────┘
```

## High Availability Architecture

```
                    Load Balancer
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
    OpenHands-1     OpenHands-2     OpenHands-3
         │                │                │
         └────────────────┼────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
    ┌──────────────────┐    ┌──────────────────┐
    │   PostgreSQL     │    │      Redis       │
    │                  │    │                  │
    │  ┌────────────┐  │    │  ┌────────────┐ │
    │  │   Master   │  │    │  │   Master   │ │
    │  └─────┬──────┘  │    │  └─────┬──────┘ │
    │        │         │    │        │        │
    │   ┌────┼────┐    │    │   ┌────┼────┐   │
    │   ▼    ▼    ▼    │    │   ▼    ▼    ▼   │
    │  R1   R2   R3    │    │  R1   R2   R3   │
    │                  │    │                  │
    │  Connection Pool │    │  Connection Pool │
    └──────────────────┘    └──────────────────┘
```

This architecture ensures:
- High availability through replication
- Load distribution across multiple instances
- Data persistence and disaster recovery
- Scalability for growing workloads
