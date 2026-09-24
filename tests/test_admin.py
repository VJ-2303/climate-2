from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_admin_auth_success_zonal():
    # Zone 1 PIN is 1001
    res = client.post("/api/admin/auth", json={"pin": "1001"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "authenticated"
    assert data["role"] == "zonal_officer"
    assert data["zone_id"] == 1
    assert "East" in data["zone_name"]
    assert "officer" in data
    assert data["officer"]["officer_name"] == "Dr. K. Murugan"

def test_admin_auth_success_master():
    # Master DDMA PIN is 9999
    res = client.post("/api/admin/auth", json={"pin": "9999"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "authenticated"
    assert data["role"] == "ddma_admin"
    assert data["zone_id"] == 0

def test_admin_auth_invalid_pin():
    res = client.post("/api/admin/auth", json={"pin": "0000"})
    assert res.status_code == 401
    assert "Invalid" in res.json()["detail"]

def test_admin_get_zones_summary():
    res = client.get("/api/admin/zones")
    assert res.status_code == 200
    zones = res.json()["zones"]
    assert len(zones) == 5
    z1 = next(z for z in zones if z["zone_id"] == 1)
    assert z1["total_facilities"] > 0
    assert "officer_name" in z1

def test_admin_get_facilities_by_zone():
    res = client.get("/api/admin/zones/1/facilities")
    assert res.status_code == 200
    facilities = res.json()["facilities"]
    assert len(facilities) > 0
    for f in facilities:
        assert f["zone_id"] == 1
        assert "category" in f
        assert "status" in f

def test_admin_update_facility_contact_and_validation():
    # Fetch first facility in Zone 1
    res = client.get("/api/admin/zones/1/facilities")
    fac_id = res.json()["facilities"][0]["id"]

    # Invalid short phone number
    res_bad = client.put(f"/api/admin/facilities/{fac_id}/contact", json={
        "contact_person": "Test Admin",
        "phone": "123"
    })
    assert res_bad.status_code == 400

    # Valid phone number
    res_good = client.put(f"/api/admin/facilities/{fac_id}/contact", json={
        "contact_person": "Dr. Testing",
        "phone": "+91 94444 88888"
    })
    assert res_good.status_code == 200
    data = res_good.json()
    assert data["status"] == "verified"
    assert data["phone"] == "+91 94444 88888"
    assert data["contact_person"] == "Dr. Testing"

def test_admin_dispatch_requires_contact():
    # Create or find an unverified facility
    res = client.get("/api/admin/zones/1/facilities?status=unverified")
    unverified = res.json()["facilities"]
    if unverified:
        target_id = unverified[0]["id"]
        res_alert = client.post("/api/admin/alerts/dispatch", json={"facility_id": target_id})
        assert res_alert.status_code == 400
        assert "contact" in res_alert.json()["detail"].lower()

def test_admin_dispatch_facility_success():
    # Update a facility with valid contact then alert it
    res = client.get("/api/admin/zones/2/facilities")
    fac = res.json()["facilities"][0]
    fac_id = fac["id"]

    client.put(f"/api/admin/facilities/{fac_id}/contact", json={
        "contact_person": "Dean In Charge",
        "phone": "+91 98420 99999"
    })

    res_alert = client.post("/api/admin/alerts/dispatch", json={"facility_id": fac_id})
    assert res_alert.status_code == 200
    data = res_alert.json()
    assert data["status"] == "dispatched"
    assert "alert_id" in data
    assert "message_en" in data
    assert "message_ta" in data
    assert "வெப்ப" in data["message_ta"]

def test_admin_bulk_category_dispatch():
    # Bulk alert all verified hospitals in Zone 3
    res_bulk = client.post("/api/admin/alerts/dispatch", json={
        "zone_id": 3,
        "category": "Hospital / Clinic"
    })
    assert res_bulk.status_code == 200
    data = res_bulk.json()
    assert data["status"] == "dispatched"
    assert data["recipients_count"] >= 1
    assert "message_en" in data

def test_admin_alerts_audit_log():
    res = client.get("/api/admin/alerts/audit?limit=10")
    assert res.status_code == 200
    logs = res.json()["logs"]
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "alert_id" in logs[0]
    assert "message_ta" in logs[0]
