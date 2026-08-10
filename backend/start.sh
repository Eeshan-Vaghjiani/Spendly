#!/bin/sh
set -eu

python -m flask --app backend.run:app db upgrade --directory backend/migrations
exec gunicorn --bind "0.0.0.0:${PORT:-5000}" --workers 1 --threads 4 --timeout 120 backend.run:app
