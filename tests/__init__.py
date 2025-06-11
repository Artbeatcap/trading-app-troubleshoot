"""Test initialization helpers."""

import os

# Use an in-memory SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import app, db

# Disable CSRF for easier form submissions during tests
app.config["WTF_CSRF_ENABLED"] = False

app.app_context().push()
db.create_all()
