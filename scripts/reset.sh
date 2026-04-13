#!/usr/bin/env bash
set -euo pipefail

docker-compose exec -T backend python manage.py flush --no-input
docker-compose exec -T backend python manage.py migrate
docker-compose exec -T backend python manage.py seed_data
docker-compose exec -T backend find /app/media/reports -type f -delete 2>/dev/null || true
docker-compose exec -T backend find /app/media/exports -type f -delete 2>/dev/null || true
