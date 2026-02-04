# File-Based vs PostgreSQL Storage

This document lists all places where OpenHands uses **file-based storage** by default instead of PostgreSQL. When running with `DB_*` environment variables, only some components use the database; others continue to use files.

## Summary

| Component | Default (File) | PostgreSQL Alternative | Config Override |
|-----------|----------------|------------------------|-----------------|
| **Secrets** (tokens, API keys) | FileSecretsStore | PostgresSecretsStore | None (hardcoded) |
| **Settings** (LLM, app config) | FileSettingsStore | PostgresSettingsStore | None (hardcoded) |
| **Conversations** (metadata, list) | FileConversationStore | — | None (hardcoded) |
| **Conversation events** | FileStore (events/*.json) | — | N/A |
| **Conversation state** | FileStore (agent_state.pkl, etc.) | — | N/A |
| **JWT secret** | FileStore | — | N/A |

---

## 1. Server Config (Hardcoded Defaults)

**File:** `openhands/server/config/server_config.py`

All three store classes are hardcoded with no environment variable override:

```python
settings_store_class: str = (
    'openhands.storage.settings.file_settings_store.FileSettingsStore'
)
secret_store_class: str = (
    'openhands.storage.secrets.file_secrets_store.FileSecretsStore'
)
conversation_store_class: str = (
    'openhands.storage.conversation.file_conversation_store.FileConversationStore'
)
```

**PostgreSQL alternatives exist for:**
- `openhands.storage.settings.postgres_settings_store.PostgresSettingsStore`
- `openhands.storage.secrets.postgres_secrets_store.PostgresSecretsStore`

**Note:** `PostgresSecretsStore` uses a different API (`get_secret`, `store_secret`) and does not implement the `load()`/`store()` interface required by the secrets routes. It cannot be used as a drop-in replacement without code changes.

---

## 2. Secrets Store (FileSecretsStore)

**File:** `openhands/storage/secrets/file_secrets_store.py`
**Storage path:** `{file_store_path}/secrets.json`
**Default:** `~/.openhands/secrets.json`

**What it stores:**
- Git provider tokens (GitHub, GitLab, Bitbucket, Azure DevOps, Forgejo)
- Custom secrets (API keys, etc.)

**Used by:**
- `POST /api/add-git-providers` – save Git tokens
- `GET /api/secrets` – list custom secrets
- `POST /api/secrets` – create custom secret
- `PUT /api/secrets/{id}` – update custom secret
- `DELETE /api/secrets/{id}` – delete custom secret

---

## 3. Settings Store (FileSettingsStore)

**File:** `openhands/storage/settings/file_settings_store.py`
**Storage path:** `{file_store_path}/settings.json`
**Default:** `~/.openhands/settings.json`

**What it stores:**
- LLM configuration (model, API keys)
- Application settings (language, analytics consent, etc.)
- Git user name/email
- Sandbox configuration

**Used by:**
- `GET /api/settings` – load settings
- `POST /api/settings` – save settings

---

## 4. Conversation Store (FileConversationStore)

**File:** `openhands/storage/conversation/file_conversation_store.py`
**Storage path:** `{file_store_path}/sessions/{conversation_id}/metadata.json`
**Default:** `~/.openhands/sessions/{conversation_id}/metadata.json`

**What it stores:**
- Conversation metadata (title, created_at, user_id, etc.)
- Used for listing conversations and checking existence

**Used by:**
- Conversation listing and search
- Conversation existence checks
- Metadata save/delete

**Note:** No PostgreSQL implementation exists for `ConversationStore` in the OSS codebase.

---

## 5. File Store (Shared Base)

**Config:** `openhands/core/config/openhands_config.py`
**Default path:** `~/.openhands` (from `file_store_path`)
**Env vars:** `FILE_STORE`, `FILE_STORE_PATH`

The file store is the underlying storage for all file-based components. It also stores:

| Path pattern | Content |
|--------------|---------|
| `sessions/{sid}/events/*.json` | Conversation event stream |
| `sessions/{sid}/metadata.json` | Conversation metadata |
| `sessions/{sid}/init.json` | Conversation init data |
| `sessions/{sid}/agent_state.pkl` | Agent state |
| `sessions/{sid}/llm_registry.json` | LLM registry |
| `sessions/{sid}/conversation_stats.pkl` | Conversation stats |
| `users/{user_id}/conversations/{sid}/...` | User-scoped conversations (when `user_id` present) |
| `secrets.json` | Secrets (via FileSecretsStore) |
| `settings.json` | Settings (via FileSettingsStore) |

**Locations module:** `openhands/storage/locations.py`

---

## 6. JWT Secret (File-Only)

**File:** `openhands/core/config/utils.py`
**Function:** `get_or_create_jwt_secret()`
**Storage path:** `{file_store_path}/.jwt_secret` (from `JWT_SECRET` constant)

Used for encrypting secrets. Always read/written via `FileStore`; no PostgreSQL option.

---

## 7. Conversation Stats

**File:** `openhands/server/services/conversation_stats.py`
**Storage path:** `{file_store_path}/sessions/{sid}/conversation_stats.pkl` (or user-scoped path)

Metrics and stats for conversations. Uses `FileStore` directly.

---

## 8. Agent State

**File:** `openhands/controller/state/state.py`
**Storage path:** `{file_store_path}/sessions/{sid}/agent_state.pkl`

Agent loop state persistence. Uses `FileStore` directly.

---

## 9. Event Stream

**File:** `openhands/events/stream.py`
**Storage path:** `{file_store_path}/sessions/{sid}/events/{id}.json`

Individual events and cache. Uses `FileStore` directly.

---

## Enabling PostgreSQL (Where Supported)

The deployment guide (`docs/DEPLOYMENT_GUIDE.md`) describes using PostgreSQL for settings and secrets by overriding the config class. However:

1. **No env var support** – The `ServerConfig` in `server_config.py` does not read `SETTINGS_STORE_CLASS`, `SECRET_STORE_CLASS`, or `CONVERSATION_STORE_CLASS` from the environment.
2. **Custom config class** – You must set `OPENHANDS_CONFIG_CLS` to a custom config class that overrides these values.
3. **PostgresSecretsStore** – Does not implement `load()`/`store()`; the secrets routes would fail if used as-is.

---

## Recommendations

To use PostgreSQL for secrets and settings:

1. Add environment variable support in `server_config.py`, e.g.:
   - `SETTINGS_STORE_CLASS`
   - `SECRET_STORE_CLASS`
   - `CONVERSATION_STORE_CLASS`

2. Implement `load()` and `store()` in `PostgresSecretsStore` (or an adapter) to match the `Secrets` model and the existing secrets API.

3. Ensure `PostgresSettingsStore` and `PostgresSecretsStore` receive a database session (e.g. via request-scoped dependency injection) when used with the legacy V0 server.
