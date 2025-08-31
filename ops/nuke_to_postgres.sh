#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Nuke-to-Postgres: force this app to use PostgreSQL only (no SQLite fallback)
# Idempotent – safe to re-run.
#
# Edit these defaults to match your server layout if auto-detection is wrong.
# ─────────────────────────────────────────────────────────────────────────────

# Attempt best-guess defaults; override as needed
APP_DIR="${APP_DIR:-/var/www/optionsplunge}"
VENV_DIR="${VENV_DIR:-/var/www/venvs/optionsplunge}"
SERVICE_NAME="${SERVICE_NAME:-optionsplunge}"
FRAMEWORK="${FRAMEWORK:-auto}"

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_DB="${PG_DB:-trading_analysis}"
PG_USER="${PG_USER:-trading_user}"
PG_PASS="${PG_PASS:-CHANGEME_STRONG_PASSWORD}"

# Compose DATABASE_URL
DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"

# Colors
info(){ echo -e "\033[1;34m[INFO]\033[0m $*"; }
warn(){ echo -e "\033[1;33m[WARN]\033[0m $*"; }
err() { echo -e "\033[1;31m[ERR ]\033[0m $*"; }

# ─────────────────────────────────────────────────────────────────────────────
# Detect framework (flask vs django)
# ─────────────────────────────────────────────────────────────────────────────
detect_framework() {
  if [[ "${FRAMEWORK}" != "auto" ]]; then
    echo "${FRAMEWORK}"
    return 0
  fi
  if grep -R "from flask import" -n "${APP_DIR}" >/dev/null 2>&1 || \
     grep -R "Flask(__name__)" -n "${APP_DIR}" >/dev/null 2>&1; then
    echo "flask"
    return 0
  fi
  if [[ -f "${APP_DIR}/manage.py" ]] && grep -R "INSTALLED_APPS" -n "${APP_DIR}" >/dev/null 2>&1; then
    echo "django"
    return 0
  fi
  # Default to flask
  echo "flask"
}

FRAMEWORK="$(detect_framework)"
info "Framework detected: ${FRAMEWORK}"

# ─────────────────────────────────────────────────────────────────────────────
# Ensure Postgres is reachable
# ─────────────────────────────────────────────────────────────────────────────
info "Ensuring postgres service is running"
if ! systemctl is-active --quiet postgresql; then
  systemctl start postgresql || true
  sleep 2
fi

if ! command -v psql >/dev/null 2>&1; then
  warn "psql not found – attempting install"
  apt-get update -y && apt-get install -y postgresql-client || true
fi

export PGPASSWORD="${PG_PASS}"
if ! psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres -c "SELECT 1" >/dev/null 2>&1; then
  warn "Attempting to create role/database if missing"
  # Create role and db via postgres superuser when possible
  if command -v sudo >/dev/null 2>&1; then
    sudo -u postgres psql -qtAc "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${PG_USER}') THEN EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', '${PG_USER}', '${PG_PASS}'); END IF; END \$\$;" || true
    sudo -u postgres psql -qtAc "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname='${PG_DB}') THEN EXECUTE format('CREATE DATABASE %I OWNER %I', '${PG_DB}', '${PG_USER}'); END IF; END \$\$;" || true
  fi
fi

info "Testing DB connectivity"
if ! psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -c "SELECT 1" >/dev/null 2>&1; then
  err "Cannot connect to postgres at ${PG_HOST}:${PG_PORT} for db ${PG_DB} as ${PG_USER}. Aborting."
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Stop service
# ─────────────────────────────────────────────────────────────────────────────
info "Stopping service ${SERVICE_NAME}.service (if running)"
systemctl stop "${SERVICE_NAME}.service" || true

# ─────────────────────────────────────────────────────────────────────────────
# Activate venv and ensure deps
# ─────────────────────────────────────────────────────────────────────────────
if [[ ! -d "${VENV_DIR}" ]]; then
  info "Creating venv at ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip wheel >/dev/null
python -m pip install psycopg[binary] >/dev/null 2>&1 || python -m pip install psycopg2-binary >/dev/null 2>&1 || true
if [[ "${FRAMEWORK}" == "flask" ]]; then
  python -m pip install Flask-Migrate python-dotenv >/dev/null 2>&1 || true
else
  python -m pip install dj-database-url python-dotenv >/dev/null 2>&1 || true
fi

# Install app requirements if present
if [[ -f "${APP_DIR}/requirements.txt" ]]; then
  info "Installing application requirements"
  python -m pip install -r "${APP_DIR}/requirements.txt" >/dev/null 2>&1 || true
fi

# ─────────────────────────────────────────────────────────────────────────────
# Systemd drop-in for DATABASE_URL
# ─────────────────────────────────────────────────────────────────────────────
info "Writing systemd drop-in for ${SERVICE_NAME}.service"
DROPIN_DIR="/etc/systemd/system/${SERVICE_NAME}.service.d"
mkdir -p "${DROPIN_DIR}"
cat >"${DROPIN_DIR}/override.conf" <<EOF
[Service]
Environment=DATABASE_URL=${DATABASE_URL}
EOF
systemctl daemon-reload

# ─────────────────────────────────────────────────────────────────────────────
# Remove any SQLite files and guard against references
# ─────────────────────────────────────────────────────────────────────────────
info "Removing SQLite files from ${APP_DIR}"
find "${APP_DIR}" -type f \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "db.sqlite3" \) -delete || true

info "Checking for lingering sqlite references (will fail if found)"
if grep -RIE "sqlite://|sqlite3" "${APP_DIR}" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=docs --exclude-dir=tests --exclude-dir=ops \
  --exclude='*.md' --exclude='migrate_*.py' --exclude='.*' --exclude='test_*.py' --exclude='*_test.py' >/tmp/sqlite_hits.txt 2>/dev/null; then
  err "Found references to sqlite in code. Please remove them:"
  cat /tmp/sqlite_hits.txt
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Write/ensure .env DATABASE_URL
# ─────────────────────────────────────────────────────────────────────────────
info "Writing ${APP_DIR}/.env with DATABASE_URL"
touch "${APP_DIR}/.env"
if grep -q '^DATABASE_URL=' "${APP_DIR}/.env"; then
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" "${APP_DIR}/.env"
else
  echo "DATABASE_URL=${DATABASE_URL}" >> "${APP_DIR}/.env"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Run migrations
# ─────────────────────────────────────────────────────────────────────────────
info "Running migrations for ${FRAMEWORK}"
export DATABASE_URL
cd "${APP_DIR}"
if [[ "${FRAMEWORK}" == "django" ]]; then
  if [[ -f manage.py ]]; then
    python manage.py collectstatic --noinput || true
    python manage.py makemigrations || true
    python manage.py migrate --noinput
  else
    err "manage.py not found – cannot run Django migrations"
    exit 1
  fi
else
  # Flask: prefer Flask-Migrate; fallback to create_all
  export FLASK_APP=${FLASK_APP:-app.py}
  if flask db upgrade >/dev/null 2>&1; then
    info "Flask-Migrate upgrade completed"
  else
    warn "Flask-Migrate not configured – attempting create_all() fallback"
    python - <<'PY'
import os
os.environ.setdefault('DATABASE_URL', os.getenv('DATABASE_URL',''))
from app import app
from models import db
with app.app_context():
    db.create_all()
print('create_all() done')
PY
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Sanity: list tables
# ─────────────────────────────────────────────────────────────────────────────
info "Listing tables in ${PG_DB}"
PGPASSWORD="${PG_PASS}" psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -c "\\dt" || true

# ─────────────────────────────────────────────────────────────────────────────
# Restart service
# ─────────────────────────────────────────────────────────────────────────────
info "Starting service ${SERVICE_NAME}.service"
systemctl start "${SERVICE_NAME}.service"
sleep 1
systemctl status "${SERVICE_NAME}.service" --no-pager || true

info "Done."


