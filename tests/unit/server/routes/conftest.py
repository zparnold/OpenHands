"""Conftest for server route tests.

Ensures APP_MODE=oss so tests use file-based stores instead of Postgres.
This must run before any openhands.server imports that load server_config.
"""

import os

# Force file-based stores for route tests (avoids Postgres/DB session requirements)
# Use direct assignment to override any existing APP_MODE=saas in the environment
os.environ['APP_MODE'] = 'oss'
