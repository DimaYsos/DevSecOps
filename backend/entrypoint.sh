#!/usr/bin/env bash
set -e

python manage.py makemigrations accounts tickets assets reports webhooks audit --noinput
python manage.py migrate --noinput

FLAG="flag{$(python -c "import secrets; print(secrets.token_hex(16))")}"

echo "$FLAG" > /flag.txt
chmod 444 /flag.txt

mkdir -p /app/media/.backups
echo "$FLAG" > /app/media/.backups/db_dump.bak

mkdir -p /flags
echo "$FLAG" > /flags/flag.txt

export CTF_FLAG="$FLAG"
CTF_FLAG="$FLAG" python manage.py seed_data

exec "$@"
