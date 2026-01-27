#!/bin/bash
set -e
echo "Waiting for database..."
while ! nc -z $SQL_HOST $SQL_PORT; do
  sleep 0.1
done
echo "Database started"
echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput
echo "Starting application..."
exec "$@"