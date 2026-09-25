import pytest
from unittest.mock import MagicMock, patch
from api.sms import format_phone_number, send_twilio_sms, send_bulk_twilio_sms

def test_format_phone_number_various_formats():
    assert format_phone_number("+91 94431 20101") == "+919443120101"
    assert format_phone_number("9443120101") == "+919443120101"
    assert format_phone_number("919443120101") == "+919443120101"
    assert format_phone_number("+1 (555) 234-5678") == "+15552345678"

def test_send_twilio_sms_simulated_when_no_credentials(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    res = send_twilio_sms("+919443120101", "Madurai Heat Warning")
    assert res["success"] is True
    assert res["mode"] == "simulated"
    assert res["sid"].startswith("SM_SIM_")
    assert res["to"] == "+919443120101"

@patch("api.sms.Client")
def test_send_twilio_sms_live_success(mock_client_class, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmockaccount123456789012345678")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mockauthtoken123456789012345678")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")

    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM1234567890abcdef1234567890abcdef"
    mock_msg.status = "queued"
    mock_client.messages.create.return_value = mock_msg
    mock_client_class.return_value = mock_client

    res = send_twilio_sms("+91 94431 20101", "Official Heatwave Advisory")
    assert res["success"] is True
    assert res["mode"] == "live"
    assert res["sid"] == "SM1234567890abcdef1234567890abcdef"
    assert res["to"] == "+919443120101"
    mock_client.messages.create.assert_called_once_with(
        to="+919443120101",
        from_="+15005550006",
        body="Official Heatwave Advisory",
    )

@patch("api.sms.Client")
def test_send_twilio_sms_live_failure_handling(mock_client_class, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmockaccount123456789012345678")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mockauthtoken123456789012345678")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Authenticate")
    mock_client_class.return_value = mock_client

    res = send_twilio_sms("+919443120101", "Alert")
    assert res["success"] is False
    assert res["mode"] == "live"
    assert "Authenticate" in res["error"]

@patch("api.sms.Client")
def test_endpoint_single_facility_dispatches_twilio(mock_client_class, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmockaccount123456789012345678")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mockauthtoken123456789012345678")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")

    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM_MOCK_SINGLE_12345"
    mock_msg.status = "queued"
    mock_client.messages.create.return_value = mock_msg
    mock_client_class.return_value = mock_client

    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    # Ensure facility has a verified contact
    client.put("/api/admin/facilities/FAC-Z1-001/contact", json={
        "contact_person": "Dean Testing",
        "phone": "+91 94431 00001"
    })

    res = client.post("/api/admin/alerts/dispatch", json={"facility_id": "FAC-Z1-001"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "dispatched"
    assert "twilio_dispatches" in data
    assert len(data["twilio_dispatches"]) == 1
    assert data["twilio_dispatches"][0]["to"] == "+919443100001"
    assert data["twilio_dispatches"][0]["sid"] == "SM_MOCK_SINGLE_12345"
    assert mock_client.messages.create.called

@patch("api.sms.Client")
def test_endpoint_bulk_category_dispatches_twilio(mock_client_class, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmockaccount123456789012345678")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mockauthtoken123456789012345678")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")

    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM_MOCK_BULK_67890"
    mock_msg.status = "queued"
    mock_client.messages.create.return_value = mock_msg
    mock_client_class.return_value = mock_client

    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    res = client.post("/api/admin/alerts/dispatch", json={"zone_id": 1, "category": "Hospital / Clinic"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "dispatched"
    assert "twilio_dispatches" in data
    assert len(data["twilio_dispatches"]) >= 1
    for item in data["twilio_dispatches"]:
        assert item["to"].startswith("+")
        assert item["sid"] == "SM_MOCK_BULK_67890"
    assert mock_client.messages.create.call_count >= 1

@patch("api.sms.Client")
def test_endpoint_sector_alert_dispatches_twilio(mock_client_class, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACmockaccount123456789012345678")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mockauthtoken123456789012345678")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15005550006")

    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.sid = "SM_MOCK_SECTOR_11223"
    mock_msg.status = "queued"
    mock_client.messages.create.return_value = mock_msg
    mock_client_class.return_value = mock_client

    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    res = client.post("/api/alerts/dispatch", json={
        "block_id": "KIB-0001",
        "message": "Extreme heat warning",
        "phone_number": "+91 98421 99999"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "dispatched"
    assert data["recipient_phone"] == "+919842199999"
    assert data["twilio_sid"] == "SM_MOCK_SECTOR_11223"
    assert mock_client.messages.create.called
