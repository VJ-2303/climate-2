from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_get_forecast_summary_endpoint():
    response = client.get("/api/forecast/summary")
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "summary" in data
    assert "daily" in data
    assert len(data["daily"]) == 5
    assert "wbgt_max" in data["daily"][0]
    assert "current" in data
    assert "temperature_celsius" in data["current"]
    assert "wbgt_celsius" in data["current"]

def test_get_forecast_days_endpoint():
    response = client.get("/api/forecast/days")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert len(data["days"]) == 5
    assert data["days"][0]["day"] == 1
    assert "date" in data["days"][0]
    assert "temp_max" in data["days"][0]
    assert "wbgt_max" in data["days"][0]
    assert "risk_tier" in data["days"][0]
    assert "current" in data
    assert "temperature_celsius" in data["current"]

def test_block_endpoint_includes_realtime_weather():
    response = client.get("/api/blocks/KIB-0001")
    assert response.status_code == 200
    data = response.json()
    assert "realtime_weather" in data
    assert "temperature_celsius" in data["realtime_weather"]
