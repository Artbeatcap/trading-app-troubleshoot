from datetime import datetime, timedelta
from app import app


def test_options_pnl_structure():
    client = app.test_client()
    exp_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    payload = {
        "option_type": "call",
        "strike": 100,
        "current_price": 105,
        "expiration_date": exp_date,
        "premium": 5,
        "quantity": 1,
    }
    response = client.post("/tools/options-pnl", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    analysis = data["analysis"]
    time_points = analysis["option_info"]["time_points"]
    for price_data in analysis["pnl_data"]:
        assert "stock_price" in price_data
        assert "time_data" in price_data
        assert len(price_data["time_data"]) == len(time_points)


def test_far_otm_option_can_show_profit():
    client = app.test_client()
    exp_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    payload = {
        "option_type": "call",
        "strike": 200,
        "current_price": 100,
        "expiration_date": exp_date,
        "premium": 1,
        "quantity": 1,
    }
    response = client.post("/tools/options-pnl", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    pnl_data = data["analysis"]["pnl_data"]
    # ensure at least one projected scenario shows positive P&L
    assert any(
        cell["pnl"] > 0
        for row in pnl_data
        if row["stock_price"] > payload["current_price"]
        for cell in row["time_data"]
    )
