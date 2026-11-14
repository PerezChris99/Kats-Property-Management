#!/usr/bin/env bash
# Managed PostgreSQL, not a Docker Compose 'db' service.
# Requires DATABASE_URL with sslmode=verify-full and AGE_RECIPIENT.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
umask 077
exec python3 "$here/managed_postgres.py" backup --directory "${KATS_BACKUP_DIR:-$here/../backups}"
