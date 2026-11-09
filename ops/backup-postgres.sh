#!/usr/bin/env bash
# Encrypt the PostgreSQL dump using an off-host encryption recipient.
set -euo pipefail
: "$AGE_RECIPIENT"
command -v age >/dev/null || { echo "Install the age encryption CLI." >&2; exit 2; }
command -v docker >/dev/null || { echo "Docker Compose required." >&2; exit 2; }
umask 077
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
temp="backups/.kats-$stamp.dump.age"
out="backups/kats-$stamp.dump.age"
trap 'rm -f "$temp"' EXIT
docker compose exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' | age -r "$AGE_RECIPIENT" > "$temp"
test -s "$temp" || { echo "Encrypted backup is empty." >&2; exit 1; }
mv "$temp" "$out"
trap - EXIT
echo "Encrypted backup created at $out"
echo "Store a copy off-server and perform a tested restore."
