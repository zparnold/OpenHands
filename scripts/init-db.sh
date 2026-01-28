#!/usr/bin/env bash
# Database initialization script for OpenHands
# This script initializes the PostgreSQL database with required tables and initial data

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-openhands}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-postgres}"

echo "Initializing OpenHands database..."
echo "Database: $DB_NAME at $DB_HOST:$DB_PORT"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
MAX_TRIES=30
TRIES=0
until PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c '\q' 2>/dev/null; do
  TRIES=$((TRIES + 1))
  if [ $TRIES -ge $MAX_TRIES ]; then
    echo "Error: PostgreSQL is not responding after $MAX_TRIES attempts"
    exit 1
  fi
  echo "PostgreSQL is unavailable - waiting... (attempt $TRIES/$MAX_TRIES)"
  sleep 2
done

echo "PostgreSQL is ready!"

# Create database if it doesn't exist
echo "Ensuring database $DB_NAME exists..."
PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
  PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME"

echo "Database $DB_NAME is ready!"

# Run Alembic migrations
echo "Running database migrations..."
cd /app
alembic -c openhands/app_server/app_lifespan/alembic.ini upgrade head

echo "Database initialization complete!"
