#!/bin/bash

# Exit on error
set -e

echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "Compressing static files..."
python manage.py compress --force
python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 ppsoj.wsgi