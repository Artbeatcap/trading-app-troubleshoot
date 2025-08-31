#!/usr/bin/env bash
set -euo pipefail

PG_USER="${1:?Missing PG_USER}"
PG_PASS="${2:?Missing PG_PASS}"

sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER ROLE ${PG_USER} WITH LOGIN PASSWORD '${PG_PASS}'"
echo "Password updated for role ${PG_USER}."


