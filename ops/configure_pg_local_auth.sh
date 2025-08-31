#!/usr/bin/env bash
set -euo pipefail

# Configure PostgreSQL to accept password auth from localhost and listen on localhost

# Determine config directory
CONF_FILE=$(sudo -u postgres psql -tAc "SHOW config_file;" | tr -d ' ')
if [[ -z "$CONF_FILE" || ! -f "$CONF_FILE" ]]; then
  echo "Could not determine PostgreSQL config_file; aborting" >&2
  exit 1
fi
CONF_DIR=$(dirname "$CONF_FILE")
HBA_FILE="$CONF_DIR/pg_hba.conf"

# Ensure listen_addresses includes localhost
sudo sed -i "s/^#*\s*listen_addresses\s*=.*/listen_addresses = 'localhost'/" "$CONF_FILE"

# Ensure password auth for IPv4/IPv6 localhost
if ! grep -q "^host\s\+all\s\+all\s\+127.0.0.1/32" "$HBA_FILE"; then
  echo "host    all             all             127.0.0.1/32            scram-sha-256" | sudo tee -a "$HBA_FILE" >/dev/null
fi
if ! grep -q "^host\s\+all\s\+all\s\+::1/128" "$HBA_FILE"; then
  echo "host    all             all             ::1/128                 scram-sha-256" | sudo tee -a "$HBA_FILE" >/dev/null
fi

sudo systemctl reload postgresql || sudo systemctl restart postgresql
echo "PostgreSQL configured for localhost password auth."


