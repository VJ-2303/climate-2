"""
Audit logging for emergency advisory dispatches using SQLite.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "audit_log.db"


def init_audit_db(db_path: Optional[str] = None) -> None:
    path = db_path or str(DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dispatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id TEXT UNIQUE,
                timestamp TEXT,
                block_id TEXT,
                recipient_group TEXT,
                recipients_count INTEGER,
                message TEXT,
                channels TEXT,
                status TEXT
            )
        """)
        conn.commit()


def record_dispatch(entry: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    path = db_path or str(DEFAULT_DB_PATH)
    init_audit_db(path)
    channels_json = json.dumps(entry.get("channels", []))
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO dispatches 
            (audit_id, timestamp, block_id, recipient_group, recipients_count, message, channels, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("audit_id"),
                entry.get("timestamp"),
                entry.get("block_id"),
                entry.get("recipient_group"),
                int(entry.get("recipients_count", 0)),
                entry.get("message"),
                channels_json,
                entry.get("status", "dispatched"),
            ),
        )
        conn.commit()
    return entry


def get_recent_dispatches(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = db_path or str(DEFAULT_DB_PATH)
    init_audit_db(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT audit_id, timestamp, block_id, recipient_group, recipients_count, message, channels, status
            FROM dispatches
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["channels"] = json.loads(item["channels"]) if item["channels"] else []
        except Exception:
            item["channels"] = []
        results.append(item)
    return results
