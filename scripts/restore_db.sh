#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  FORCE_RESTORE=1 ./scripts/restore_db.sh /path/to/backup.sql

Environment variables:
  COMPOSE_CMD     Docker Compose command. Default: docker compose
  DB_SERVICE      Compose service name for PostgreSQL. Default: db
  DB_NAME         Target database name. Default: tsm
  DB_USER         Database user. Default: postgres
  FORCE_RESTORE   Set to 1 to allow restoring into a non-empty public schema

Supported backups:
  - Plain SQL exports (.sql)
  - Custom-format pg_dump exports (.dump, .backup, .custom, or PGDMP header)
  - Gzip-compressed variants of the above (.gz)
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "$#" -ne 1 ]; then
  usage
  exit 1
fi

BACKUP_PATH="$1"
COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_NAME="${DB_NAME:-tsm}"
DB_USER="${DB_USER:-postgres}"
FORCE_RESTORE="${FORCE_RESTORE:-0}"
LOCAL_RESTORE_FILE="$BACKUP_PATH"
TEMP_FILE=""
CONTAINER_RESTORE_FILE="/tmp/tsm_restore_input"

cleanup() {
  if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
    rm -f "$TEMP_FILE"
  fi

  if command -v docker >/dev/null 2>&1; then
    $COMPOSE_CMD exec -T "$DB_SERVICE" rm -f "$CONTAINER_RESTORE_FILE" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

if [ ! -f "$BACKUP_PATH" ]; then
  echo "Backup file not found: $BACKUP_PATH" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to run this restore script." >&2
  exit 1
fi

if [[ "$BACKUP_PATH" == *.gz ]]; then
  if ! command -v gzip >/dev/null 2>&1; then
    echo "gzip is required to restore .gz backups." >&2
    exit 1
  fi

  TEMP_FILE="$(mktemp /tmp/tsm_restore.XXXXXX)"
  gzip -dc "$BACKUP_PATH" > "$TEMP_FILE"
  LOCAL_RESTORE_FILE="$TEMP_FILE"
fi

if ! $COMPOSE_CMD ps --status running "$DB_SERVICE" >/dev/null 2>&1; then
  echo "Database service '$DB_SERVICE' is not running. Start it first with: $COMPOSE_CMD up -d $DB_SERVICE" >&2
  exit 1
fi

TABLE_COUNT="$($COMPOSE_CMD exec -T "$DB_SERVICE" \
  psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")"

TABLE_COUNT="$(echo "$TABLE_COUNT" | tr -d '[:space:]')"

if [ -z "$TABLE_COUNT" ]; then
  echo "Unable to determine whether the target database is empty." >&2
  exit 1
fi

if [ "$TABLE_COUNT" != "0" ] && [ "$FORCE_RESTORE" != "1" ]; then
  echo "Target database '$DB_NAME' already contains $TABLE_COUNT table(s)." >&2
  echo "Refusing to restore into a non-empty schema without FORCE_RESTORE=1." >&2
  exit 1
fi

BACKUP_MAGIC="$(LC_ALL=C head -c 5 "$LOCAL_RESTORE_FILE" || true)"
BACKUP_TYPE="sql"

if [ "$BACKUP_MAGIC" = "PGDMP" ]; then
  BACKUP_TYPE="custom"
fi

echo "Copying backup into container..."
$COMPOSE_CMD cp "$LOCAL_RESTORE_FILE" "$DB_SERVICE:$CONTAINER_RESTORE_FILE"

echo "Restoring $BACKUP_TYPE backup into database '$DB_NAME'..."
if [ "$BACKUP_TYPE" = "custom" ]; then
  $COMPOSE_CMD exec -T "$DB_SERVICE" \
    pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    "$CONTAINER_RESTORE_FILE"
else
  $COMPOSE_CMD exec -T "$DB_SERVICE" \
    psql \
    -v ON_ERROR_STOP=1 \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$CONTAINER_RESTORE_FILE"
fi

echo "Restore completed successfully."
