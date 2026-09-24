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

def test_forecast_days_includes_timeline_and_alert():
    response = client.get("/api/forecast/days")
    assert response.status_code == 200
    data = response.json()
    assert "timeline" in data
    assert len(data["timeline"]) >= 5
    assert "composite_alert" in data

def test_historical_forecast_day_attributes():
    # Day -1 represents yesterday's replay
    response = client.get("/api/layers/forecast_day_-1/attributes")
    assert response.status_code == 200
    data = response.json()
    assert "KIB-0001" in data
    assert isinstance(data["KIB-0001"], (int, float))

def test_alerts_dispatch_and_audit():
    # Dispatch an alert
    disp_res = client.post("/api/alerts/dispatch", json={
        "block_id": "KIB-0001",
        "recipient_group": "vulnerable_households",
        "message": "Extreme heatwave alert. Stay hydrated."
    })
    assert disp_res.status_code == 200
    audit_id = disp_res.json()["audit_id"]

    # Verify audit log contains the dispatched alert
    audit_res = client.get("/api/alerts/audit?limit=10")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert "logs" in audit_data
    assert any(log["audit_id"] == audit_id for log in audit_data["logs"])

def test_public_view_endpoint():
    response = client.get("/public")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
