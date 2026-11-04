#!/bin/sh
set -e

# Wait for PostgreSQL to be ready
# Using pg_isready from postgresql-client; install in Dockerfile if not present (we have libpq-dev & gcc, we can install postgresql-client)
# Simple retry loop
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-ticketdesk_user}"; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Apply migrations
python manage.py migrate --noinput

# Start the development server (or gunicorn for production)
exec "$@"

