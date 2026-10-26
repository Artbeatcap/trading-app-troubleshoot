"""Basic application smoke tests."""

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app import app
from app import db
from models import Trade, TradingJournal, User


PRIVATE_MARKERS = (
    "ZZLEAK",
    "9999.99",
    "8888.88",
    "1234.56",
    "Private journal marker",
    "Confidential market marker",
    "4/10",
)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}",
        WTF_CSRF_ENABLED=False,
    )
    with app.app_context():
        db.create_all()

    yield

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_index_route():
    """Ensure the index page loads successfully."""
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200


@pytest.fixture()
def client_with_private_data():
    with app.app_context():
        user = User(username="privacy-user", email="privacy@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        db.session.add(
            Trade(
                user_id=user.id,
                symbol="ZZLEAK",
                trade_type="stock",
                entry_date=datetime(2026, 1, 10, 9, 30),
                entry_price=9999.99,
                quantity=1,
                exit_date=datetime(2026, 1, 11, 16, 0),
                exit_price=8888.88,
                profit_loss=1234.56,
                setup_type="private_setup",
                notes="Private trade marker",
            )
        )
        db.session.add(
            TradingJournal(
                user_id=user.id,
                journal_date=date(2026, 1, 10),
                market_notes="Confidential market marker",
                trading_notes="Private journal marker",
                daily_score=4,
            )
        )
        db.session.commit()

    yield app.test_client()


@pytest.mark.parametrize("path", ["/dashboard", "/trades", "/journal"])
def test_guest_pages_do_not_render_private_trade_or_journal_data(client_with_private_data, path):
    response = client_with_private_data.get(path)

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    for marker in PRIVATE_MARKERS:
        assert marker not in body


@pytest.mark.parametrize(
    ("path", "sample_marker"),
    [
        ("/dashboard", "AAPL"),
        ("/trades", "Sample Trades"),
        ("/journal", "Sample Journal Entries"),
    ],
)
def test_guest_pages_render_demo_content(client_with_private_data, path, sample_marker):
    response = client_with_private_data.get(path)

    assert response.status_code == 200
    assert sample_marker in response.get_data(as_text=True)


def test_guest_journal_post_stores_session_draft_without_creating_row():
    client = app.test_client()

    response = client.post(
        "/journal/add",
        data={
            "journal_date": "2026-01-12",
            "market_notes": "Guest market draft",
            "trading_notes": "Guest trading draft",
            "emotions": "calm",
            "lessons_learned": "wait for confirmation",
            "tomorrow_plan": "review watchlist",
            "daily_pnl": "12.34",
            "daily_score": "6",
        },
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess["pending_journal"]["trading_notes"] == "Guest trading draft"

    with app.app_context():
        assert TradingJournal.query.count() == 0


def test_trading_journal_requires_user_id():
    with app.app_context():
        db.session.add(
            TradingJournal(
                journal_date=date(2026, 1, 12),
                trading_notes="Ownerless persistent journal",
            )
        )

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()
