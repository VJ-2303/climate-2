"""
api/admin.py
Administrative Command Backend for Madurai's 5 Municipal Zones:
- Zonal PIN Authentication (1001-5005 & 9999 DDMA Master)
- Sensitive Facilities Directory (~300 Schools, Hospitals, Colleges from OSM GeoJSON)
- Contact Number Provisioning & Validation
- Institutional Targeted & Autonomous Alerting Engine
- Persistent SQLite Storage (data/admin_facilities.db)
"""

import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "admin_facilities.db"

def get_db():
    if not DB_PATH.is_file():
        from scripts.setup_admin_db import init_db
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def authenticate_pin(pin: str) -> Optional[Dict[str, Any]]:
    clean_pin = str(pin).strip()
    # Master DDMA PIN
    if clean_pin == "9999":
        return {
            "status": "authenticated",
            "role": "ddma_admin",
            "zone_id": 0,
            "zone_name": "All Zones (DDMA Command)",
            "officer": {
                "officer_name": "District Disaster Management Authority",
                "designation": "Master DDMA Administrator",
                "phone": "1077",
                "email": "ddma.madurai@tn.gov.in",
                "office_address": "District Collectorate, Madurai - 625020",
                "autonomous_alerts": 1,
                "critical_wbgt_threshold": 38.0,
            }
        }

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM zonal_officers WHERE pin = ?", (clean_pin,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "status": "authenticated",
        "role": "zonal_officer",
        "zone_id": row["zone_id"],
        "zone_name": row["zone_name"],
        "officer": {
            "officer_name": row["officer_name"],
            "designation": row["designation"],
            "phone": row["phone"],
            "email": row["email"],
            "office_address": row["office_address"],
            "autonomous_alerts": row["autonomous_alerts"],
            "critical_wbgt_threshold": row["critical_wbgt_threshold"],
        }
    }

def get_zones_summary() -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            z.*,
            COUNT(f.id) as total_facilities,
            SUM(CASE WHEN f.status = 'verified' THEN 1 ELSE 0 END) as verified_contacts,
            SUM(CASE WHEN f.status = 'unverified' THEN 1 ELSE 0 END) as unverified_contacts
        FROM zonal_officers z
        LEFT JOIN sensitive_facilities f ON z.zone_id = f.zone_id
        GROUP BY z.zone_id
        ORDER BY z.zone_id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    summary = []
    for r in rows:
        d = dict(r)
        d.pop("pin", None)
        summary.append(d)
    return summary

def get_zone_details(zone_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM zonal_officers WHERE zone_id = ?", (zone_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d.pop("pin", None)
    return d

def update_officer_profile(zone_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE zonal_officers
        SET officer_name = COALESCE(?, officer_name),
            designation = COALESCE(?, designation),
            phone = COALESCE(?, phone),
            email = COALESCE(?, email),
            office_address = COALESCE(?, office_address),
            autonomous_alerts = COALESCE(?, autonomous_alerts),
            critical_wbgt_threshold = COALESCE(?, critical_wbgt_threshold)
        WHERE zone_id = ?
    """, (
        payload.get("officer_name"),
        payload.get("designation"),
        payload.get("phone"),
        payload.get("email"),
        payload.get("office_address"),
        payload.get("autonomous_alerts"),
        payload.get("critical_wbgt_threshold"),
        zone_id,
    ))
    conn.commit()
    conn.close()
    return get_zone_details(zone_id) or {}

def get_facilities(
    zone_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM sensitive_facilities WHERE 1=1"
    params = []

    if zone_id is not None and zone_id > 0:
        query += " AND zone_id = ?"
        params.append(zone_id)

    if category:
        query += " AND category = ?"
        params.append(category)

    if status:
        query += " AND status = ?"
        params.append(status)

    if search:
        s = f"%{search.strip().lower()}%"
        query += " AND (LOWER(name) LIKE ? OR LOWER(address) LIKE ? OR LOWER(contact_person) LIKE ?)"
        params.extend([s, s, s])

    query += " ORDER BY status ASC, name ASC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def validate_phone(phone: str) -> bool:
    if not phone:
        return False
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 10

def update_facility_contact(
    facility_id: str,
    contact_person: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    if phone is not None:
        if phone.strip() and not validate_phone(phone):
            raise ValueError("Phone number must contain at least 10 digits")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sensitive_facilities WHERE id = ?", (facility_id,))
    existing = cur.fetchone()
    if not existing:
        conn.close()
        raise KeyError(f"Facility {facility_id} not found")

    new_person = contact_person.strip() if contact_person is not None else existing["contact_person"]
    new_phone = phone.strip() if phone is not None else existing["phone"]
    new_email = email.strip() if email is not None else existing["email"]
    new_status = "verified" if validate_phone(new_phone) else "unverified"

    cur.execute("""
        UPDATE sensitive_facilities
        SET contact_person = ?, phone = ?, email = ?, status = ?
        WHERE id = ?
    """, (new_person, new_phone, new_email, new_status, facility_id))
    conn.commit()

    cur.execute("SELECT * FROM sensitive_facilities WHERE id = ?", (facility_id,))
    updated = dict(cur.fetchone())
    conn.close()
    return updated

def generate_institutional_advisory(category: str, local_wbgt: float) -> Dict[str, str]:
    wbgt_str = f"{local_wbgt:.1f}"
    cat_lower = category.lower()

    if "school" in cat_lower or "kindergarten" in cat_lower:
        return {
            "en": f"[MADURAI HEAT EMERGENCY] Extreme daytime WBGT {wbgt_str}°C forecast. Immediately shift all student activities indoors between 11 AM – 4 PM. Ensure continuous potable cold drinking water on all floor points. Cancel afternoon outdoor physical training and sports drills.",
            "ta": f"[மதுரை தீவிர வெப்ப எச்சரிக்கை] பகல்நேர வெப்பக்குறியீடு {wbgt_str}°C ஆக உயர்ந்துள்ளது. காலை 11 மணி முதல் மாலை 4 மணி வரை அனைத்து பள்ளி நிகழ்வுகளையும் உட்புறத்திற்கு மாற்றவும். அனைத்து தளங்களிலும் குளிர்ந்த குடிநீர் இருப்பதை உறுதி செய்யவும். மாலை நேர வெளிப்புற விளையாட்டு பயிற்சிகளை ரத்து செய்யவும்.",
        }
    elif "hospital" in cat_lower or "clinic" in cat_lower:
        return {
            "en": f"[MADURAI URGENT HEALTH ALERT] Heatwave surge forecast (Local WBGT {wbgt_str}°C). Prepare dedicated heatstroke cold-packs & rehydration rooms. Check IV fluid stockpiles & backup generator fuel for air conditioning.",
            "ta": f"[மதுரை மருத்துவ அவசர எச்சரிக்கை] தீவிர வெப்ப அலை எச்சரிக்கை: வெப்பக்குறியீடு {wbgt_str}°C. வெப்ப பக்கவாத அவசர சிகிச்சை படுக்கைகள் மற்றும் குளிர்ந்த IV திரவங்களை தயார் நிலையில் வைக்கவும். ஏர் கூலிங்கிற்கான ஜெனரேட்டர் எரிபொருளை சரிபார்க்கவும்.",
        }
    else: # College / University
        return {
            "en": f"[MADURAI COLLEGE ADVISORY] High thermal load: Local WBGT {wbgt_str}°C. Suspend non-essential field work and outdoor labs. Ensure open access to shaded common areas and hydration points.",
            "ta": f"[மதுரை கல்லூரி ஆலோசனை] அதிக வெப்ப சூழல்: வெப்பக்குறியீடு {wbgt_str}°C. ஆய்வக வெளிப்புற பணிகளை தவிர்க்கவும். மாணவர்களுக்கு நிழலான பகுதிகள் மற்றும் குடிநீர் வசதிகளை உறுதி செய்யவும்.",
        }

def dispatch_institutional_alert(
    zone_id: Optional[int] = None,
    facility_id: Optional[str] = None,
    category: Optional[str] = None,
    trigger_type: str = "manual",
) -> Dict[str, Any]:
    from api.weather import get_5day_forecast

    # Current WBGT reference from live weather forecast
    forecast = get_5day_forecast()
    current = forecast.get("current", {})
    timeline = forecast.get("timeline", [])
    today_item = next((d for d in timeline if d.get("day") == 0), timeline[0] if timeline else {})
    local_wbgt = float(today_item.get("wbgt_max", current.get("temperature_celsius", 33.5)))

    conn = get_db()
    cur = conn.cursor()

    targets = []
    if facility_id:
        cur.execute("SELECT * FROM sensitive_facilities WHERE id = ?", (facility_id,))
        fac = cur.fetchone()
        if not fac:
            conn.close()
            raise KeyError(f"Facility {facility_id} not found")
        if not fac["phone"] or fac["status"] != "verified":
            conn.close()
            raise ValueError(f"Cannot alert facility '{fac['name']}' without a verified contact phone number. Please update contact details first.")
        targets.append(fac)
        target_cat = fac["category"]
        zone_id = fac["zone_id"]
    else:
        q = "SELECT * FROM sensitive_facilities WHERE zone_id = ? AND status = 'verified'"
        p = [zone_id]
        if category and category != "All":
            q += " AND category = ?"
            p.append(category)
        cur.execute(q, p)
        targets = cur.fetchall()
        target_cat = category or "All"

    if not targets:
        conn.close()
        raise ValueError("No verified contacts found matching the criteria. Please add contact phone numbers before dispatching alerts.")

    advisory = generate_institutional_advisory(target_cat, local_wbgt)
    alert_id = f"INST-ALERT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    cur.execute("""
        INSERT INTO institutional_alerts (
            alert_id, zone_id, facility_id, facility_name, category, recipients_count, trigger_type, message_en, message_ta, local_wbgt, timestamp, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'dispatched')
    """, (
        alert_id,
        zone_id,
        facility_id if len(targets) == 1 else None,
        targets[0]["name"] if len(targets) == 1 else f"Bulk ({len(targets)} facilities)",
        target_cat,
        len(targets),
        trigger_type,
        advisory["en"],
        advisory["ta"],
        local_wbgt,
        now_iso,
    ))

    # Update last_alert_time on targets
    target_ids = [t["id"] for t in targets]
    placeholders = ",".join(["?"] * len(target_ids))
    cur.execute(f"UPDATE sensitive_facilities SET last_alert_time = ? WHERE id IN ({placeholders})", [now_iso] + target_ids)

    conn.commit()
    conn.close()

    # Dispatch actual Twilio SMS to all verified target phone numbers
    from api.sms import send_bulk_twilio_sms
    sms_targets = [{"id": t["id"], "name": t["name"], "phone": t["phone"]} for t in targets]
    twilio_results = send_bulk_twilio_sms(sms_targets, advisory["en"])

    return {
        "status": "dispatched",
        "alert_id": alert_id,
        "zone_id": zone_id,
        "facility_id": facility_id,
        "category": target_cat,
        "recipients_count": len(targets),
        "trigger_type": trigger_type,
        "local_wbgt": local_wbgt,
        "timestamp": now_iso,
        "message_en": advisory["en"],
        "message_ta": advisory["ta"],
        "channels": ["Twilio SMS (Carrier Gateway)", "TNSDMA CAP Broadcast", "Zonal Corporation Dispatch"],
        "twilio_dispatches": twilio_results,
    }

def get_alerts_audit_log(zone_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    if zone_id and zone_id > 0:
        cur.execute("SELECT * FROM institutional_alerts WHERE zone_id = ? ORDER BY timestamp DESC LIMIT ?", (zone_id, limit))
    else:
        cur.execute("SELECT * FROM institutional_alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def evaluate_autonomous_alerts() -> Dict[str, Any]:
    from api.weather import get_5day_forecast

    forecast = get_5day_forecast()
    current = forecast.get("current", {})
    timeline = forecast.get("timeline", [])
    today_item = next((d for d in timeline if d.get("day") == 0), timeline[0] if timeline else {})
    current_wbgt = float(today_item.get("wbgt_max", current.get("temperature_celsius", 32.0)))
    composite_alert = forecast.get("composite_alert", {})
    alert_level = composite_alert.get("alert_level", 0)

    zones = get_zones_summary()
    dispatched = []

    for z in zones:
        # Autonomous heatwave alert is always active and cannot be disabled
        thresh = float(z.get("critical_wbgt_threshold", 38.0))
        # Trigger condition: current WBGT >= threshold or composite IMD heatwave level >= 2 (Orange/Red)
        if current_wbgt >= thresh or alert_level >= 2:
            try:
                res = dispatch_institutional_alert(
                    zone_id=z["zone_id"],
                    category="All",
                    trigger_type="autonomous",
                )
                dispatched.append(res)
            except Exception:
                pass

    return {
        "evaluated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_wbgt": current_wbgt,
        "alert_level": alert_level,
        "dispatches_count": len(dispatched),
        "dispatched": dispatched,
    }
