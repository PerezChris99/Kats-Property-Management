#!/usr/bin/env bash
# Destructive restore helper intentionally refuses production.
set -euo pipefail
if [ "$#" -ne 2 ] || [ "$1" != "--confirm" ]; then
  echo "Usage: APP_ENV=staging AGE_IDENTITY=/path/key $0 --confirm encrypted-backup.age" >&2
  exit 2
fi
: "$APP_ENV"
: "$AGE_IDENTITY"
if [ "$APP_ENV" != "staging" ] && [ "$APP_ENV" != "development" ]; then
  echo "Only staging/development restores are supported by this helper." >&2
  exit 2
fi
test -f "$2" || { echo "Backup file missing." >&2; exit 2; }
command -v age >/dev/null || { echo "Install the age encryption CLI." >&2; exit 2; }
age --decrypt -i "$AGE_IDENTITY" "$2" | docker compose exec -T db sh -c 'exec pg_restore --clean --if-exists --no-owner --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
echo "Restore command completed. Validate row counts, balances, audit records and schema version."
