#!/usr/bin/env bash
set -euo pipefail

PG_USER="${1:?Missing PG_USER}"
PG_PASS="${2:?Missing PG_PASS}"
PG_DB="${3:?Missing PG_DB}"

# Create role if missing
if ! sudo -u postgres psql -qtAc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE ${PG_USER} LOGIN PASSWORD '${PG_PASS}'"
fi

# Create database if missing
if ! sudo -u postgres psql -qtAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${PG_DB} OWNER ${PG_USER}"
fi

echo "Role ${PG_USER} and database ${PG_DB} are ready."


