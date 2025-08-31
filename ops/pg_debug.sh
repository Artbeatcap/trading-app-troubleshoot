#!/usr/bin/env bash
set -euo pipefail

PG_USER="${1:-trading_user}"
PG_PASS="${2:-CHANGEME_STRONG_PASSWORD}"
PG_DB="${3:-trading_analysis}"

echo "=== PostgreSQL service ==="
systemctl status postgresql --no-pager || true

echo "=== Listening ports (5432) ==="
ss -lntp | grep 5432 || true

echo "=== listen_addresses ==="
sudo -u postgres psql -tAc "SHOW listen_addresses;" | sed 's/^/  /'

echo "=== hba_file ==="
HBA_FILE=$(sudo -u postgres psql -tAc "SHOW hba_file;" | tr -d ' ')
echo "  $HBA_FILE"

echo "=== password_encryption ==="
sudo -u postgres psql -tAc "SHOW password_encryption;" | sed 's/^/  /'

echo "=== pg_hba.conf (tail) ==="
sudo tail -n 50 "$HBA_FILE" | sed 's/^/  /' || true

echo "=== Test login as $PG_USER to $PG_DB ==="
export PGPASSWORD="$PG_PASS"
psql -h localhost -p 5432 -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;" || echo "Login failed"

echo "=== Done ==="


