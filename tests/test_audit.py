import os
import tempfile
import pytest
from api.audit import init_audit_db, record_dispatch, get_recent_dispatches

def test_audit_log_record_and_retrieve(tmp_path):
    db_file = str(tmp_path / "test_audit.db")
    init_audit_db(db_file)

    entry = {
        "audit_id": "DISP-TEST001",
        "timestamp": "2026-09-24T12:00:00Z",
        "block_id": "KIB-0001",
        "recipient_group": "vulnerable_residents",
        "recipients_count": 120,
        "message": "Extreme heat warning. Stay indoors.",
        "channels": ["SMS", "WhatsApp"],
        "status": "dispatched"
    }

    saved = record_dispatch(entry, db_path=db_file)
    assert saved["audit_id"] == "DISP-TEST001"

    logs = get_recent_dispatches(limit=10, db_path=db_file)
    assert len(logs) == 1
    assert logs[0]["audit_id"] == "DISP-TEST001"
    assert logs[0]["block_id"] == "KIB-0001"
    assert logs[0]["channels"] == ["SMS", "WhatsApp"]
