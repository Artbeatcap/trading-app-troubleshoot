"""Basic application smoke test."""

from app import app


def test_index_route():
    """Ensure the index page loads successfully."""
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
