#!/usr/bin/env bash
set -e

echo "Running collectstatic..."
python manage.py collectstatic --noinput || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Ensuring superuser..."
python manage.py ensure_superuser

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
