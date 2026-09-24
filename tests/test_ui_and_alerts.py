from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_routes_exist():
    # Root redirects or serves officer portal
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "ThermalGuard" in r_root.text or "HeatViz" in r_root.text

    # Officer portal route
    r_officer = client.get("/officer")
    assert r_officer.status_code == 200
    assert "Officer" in r_officer.text or "Command" in r_officer.text

    # Public citizen portal route
    r_public = client.get("/public")
    assert r_public.status_code == 200
    assert "Citizen" in r_public.text or "Public" in r_public.text

def test_sms_alert_dispatch_endpoint():
    payload = {
        "block_id": "KIB-0001",
        "recipient_group": "vulnerable_households",
        "message": "Dangerous WBGT 33.2C expected today. Stay hydrated."
    }
    response = client.post("/api/alerts/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dispatched"
    assert "audit_id" in data
    assert "recipients_count" in data
    assert data["recipients_count"] > 0
