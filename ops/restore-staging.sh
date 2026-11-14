#!/usr/bin/env bash
# Only restore into explicitly named *_staging or *_restore database.
# Requires APP_ENV=staging, AGE_IDENTITY and RESTORE_DATABASE_URL; never production.
set -euo pipefail
if [ "$#" -ne 2 ] || [ "$1" != "--confirm" ]; then
  echo "Usage: APP_ENV=staging AGE_IDENTITY=/private/key RESTORE_DATABASE_URL=... $0 --confirm /path/backup.dump.age" >&2
  exit 2
fi
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
umask 077
exec python3 "$here/managed_postgres.py" restore-staging --confirm RESTORE_ISOLATED_STAGING_ONLY --archive "$2"
