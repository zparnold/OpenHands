"""Unit test conftest: force file-based stores so Postgres is not used.

Setting APP_MODE=oss here ensures that when openhands.server (and thus
user_auth, server_config) is first imported, _use_postgres_settings and
_use_postgres_secrets are False. Otherwise, with APP_MODE=saas (e.g. from .env),
tests can hit PostgresSettingsStore/PostgresSecretsStore with a mocked or
missing DB session, causing "object MagicMock can't be used in 'await' expression".
"""

import os

# Must run before any openhands.server import that reads server_config
os.environ['APP_MODE'] = 'oss'
