import json
from contextlib import contextmanager
from datetime import datetime, date

import pytest
from flask import template_rendered

from app import app, db
from models import User, TradingJournal, Trade


@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


@pytest.fixture(autouse=True)
def setup_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()


def create_user(username="user", email="user@example.com", password="test"):
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_journal_add_page_renders_form():
    client = app.test_client()
    response = client.get("/journal/add")
    assert response.status_code == 200
    assert b"Journal Entry" in response.data


def test_journal_edit_page_renders_form_after_login():
    client = app.test_client()
    with app.app_context():
        user = create_user()
        journal = TradingJournal(user_id=user.id, journal_date=date.today())
        db.session.add(journal)
        db.session.commit()
        journal_date = journal.journal_date
    login(client, "user", "test")
    response = client.get(f"/journal/{journal_date}/edit")
    assert response.status_code == 200
    assert b"Journal Entry" in response.data


def test_analytics_route_returns_json_when_trades_exist():
    client = app.test_client()
    with app.app_context():
        user = create_user()
        trade = Trade(
            user_id=user.id,
            symbol="AAPL",
            trade_type="long",
            entry_date=datetime.utcnow(),
            entry_price=100,
            quantity=1,
            exit_price=110,
            exit_date=datetime.utcnow(),
        )
        trade.calculate_pnl()
        db.session.add(trade)
        db.session.commit()
    login(client, "user", "test")
    with captured_templates(app) as templates:
        response = client.get("/analytics")
        assert response.status_code == 200
        template, context = templates[0]
        data = json.loads(context["charts_json"])
        assert set(["pnl_over_time", "win_loss_pie", "setup_performance"]).issubset(data.keys())
        stats_keys = {"total_trades", "winning_trades", "losing_trades", "win_rate"}
    assert stats_keys.issubset(context["stats"].keys())


def test_trades_page_displays_saved_trades():
    client = app.test_client()
    with app.app_context():
        user = create_user()
        trade = Trade(
            user_id=user.id,
            symbol="AAPL",
            trade_type="long",
            entry_date=datetime.utcnow(),
            entry_price=100,
            quantity=1,
            exit_price=110,
            exit_date=datetime.utcnow(),
        )
        trade.calculate_pnl()
        db.session.add(trade)
        db.session.commit()
    login(client, "user", "test")
    response = client.get("/trades")
    assert response.status_code == 200
    assert b"AAPL" in response.data
